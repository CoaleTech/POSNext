import json
import frappe


def load_json(data):
    """Load JSON data or return as is if it's already a Python dictionary"""
    if isinstance(data, str):
        return json.loads(data)
    return data


def create_order_items(items):
    """Create a list of order items from a list of input items"""
    order_items = []
    for item in items:
        order_item = {
            "item_code": item.get("item", item.get("item_code")),
            "qty": item["qty"],
            "item_name": item["item_name"],
            "comments": item.get("comment", item.get("comments", "")),
        }
        order_items.append(order_item)
    return order_items


def create_kot_doc(
    invoice_id,
    customer,
    restaurant_table,
    items,
    kot_type,
    comments,
    pos_profile_id,
    kot_naming_series,
    production,
):
    """Create a KOT (Kitchen Order Ticket) document"""
    pos_invoice = frappe.get_doc("POS Invoice", invoice_id)
    order_number = pos_invoice.custom_ury_order_number
    is_aggregator = 0
    if pos_invoice.order_type == "Aggregators":
        is_aggregator = 1

    kot_doc = frappe.get_doc(
        {
            "doctype": "KOT",
            "invoice": invoice_id,
            "restaurant_table": restaurant_table,
            "customer_name": customer,
            "pos_profile": pos_profile_id,
            "comments": comments,
            "type": kot_type,
            "naming_series": kot_naming_series,
            "production": production,
            "aggregator_id": pos_invoice.custom_aggregator_id,
            "is_aggregator": is_aggregator,
            "order_no": order_number
        }
    )

    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    branch = pos_profile.branch
    if restaurant_table:
        # Get menu from table's room/restaurant
        room = frappe.db.get_value("Table", restaurant_table, "restaurant_room")
        if room:
            restaurant = frappe.db.get_value("Table", restaurant_table, "restaurant")
            menu = frappe.db.get_value("Menu for Room", {"room": room, "parent": restaurant}, "menu")
        else:
            menu = frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu")
    else:
        menu = frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu")

    for item in items:
        course = frappe.db.get_value("URY Menu Item", {"item": item["item_code"], "parent": menu}, "course")
        kot_doc.append(
            "kot_items",
            {
                "item": item["item_code"],
                "item_name": item["item_name"],
                "quantity": item["qty"],
                "comments": item["comments"],
                "course": course
            },
        )

    kot_doc.insert()
    kot_doc.submit()
    return kot_doc


def get_all_production_item_groups(branch):
    """Function to get all production item groups for a given branch"""
    production_units = frappe.get_all(
        "Production Unit", filters={"branch": branch}, fields=["name"]
    )

    all_item_groups = set()
    for production in production_units:
        production_doc = frappe.get_doc("Production Unit", production.name)
        for item_group in production_doc.item_groups:
            all_item_groups.add(item_group.item_group)

    return list(all_item_groups)


def process_items_for_kot(
    invoice_id,
    customer,
    restaurant_table,
    items,
    comments,
    pos_profile_id,
    kot_naming_series,
    kot_type,
):
    """Process items to create KOT documents"""
    kot_items = create_order_items(items)
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    productions = frappe.db.get_all(
        "Production Unit", filters={"branch": pos_profile.branch}, fields=["name"]
    )

    if productions:
        all_production_item_groups = get_all_production_item_groups(pos_profile.branch)

        # Iterate through each item and check if item group belongs to a production unit
        for item in kot_items:
            item_group = frappe.db.get_value("Item", item["item_code"], "item_group")
            item_code = item["item_code"]
            if item_group not in all_production_item_groups:
                frappe.msgprint(
                    f"Item group '{item_group}' for item '{item_code}' is not in any production."
                )

        for production in productions:
            production_item_groups_list = frappe.get_all(
                "Production Item Groups",
                filters={"parent": production.name, "parenttype": "Production Unit"},
                fields=["item_group"]
            )

            production_items = []
            for item in kot_items:
                item_group = frappe.db.get_value("Item", item["item_code"], "item_group")
                if item_group in [pig.item_group for pig in production_item_groups_list]:
                    production_items.append(item)

            if production_items:
                create_kot_doc(
                    invoice_id,
                    customer,
                    restaurant_table,
                    production_items,
                    kot_type,
                    comments,
                    pos_profile_id,
                    kot_naming_series,
                    production.name,
                )
    else:
        frappe.throw(
            f"Create Production Unit against POS Profile: {pos_profile.name}"
        )


def process_items_for_cancel_kot(
    invoice_id,
    customer,
    restaurant_table,
    cancel_items,
    comments,
    pos_profile_id,
    cancel_kot_naming_series,
    kot_type,
    invoice_items,
):
    """Process items to create a cancel KOT document"""
    pos_invoice = frappe.get_doc("POS Invoice", invoice_id)
    order_number = pos_invoice.custom_ury_order_number
    is_aggregator = 0
    if pos_invoice.order_type == "Aggregators":
        is_aggregator = 1

    kot_list = frappe.db.get_list(
        "KOT",
        filters={
            "invoice": invoice_id,
            "type": ("in", ("New Order", "Order Modified")),
        },
        fields=["name"],
    )

    # Find original KOTs related to the cancel items
    original_kots = []
    for cancel_item in cancel_items:
        for kot in kot_list:
            kot_doc = frappe.get_doc("KOT", kot.name)
            kot_cancel_items = kot_doc.kot_items
            item_check_flag = False
            for kot_item in kot_cancel_items:
                if cancel_item["item_code"] == kot_item.item:
                    item_check_flag = True
            if item_check_flag:
                original_kots.append(kot_doc.name)
                break

    # Remove duplicate KOT names and join them into a single string
    set_kots = list(set(original_kots))
    set_kots = ",".join(set_kots)

    kot_cancel_doc = frappe.get_doc(
        {
            "doctype": "KOT",
            "naming_series": cancel_kot_naming_series,
            "original_kot": set_kots,
            "restaurant_table": restaurant_table,
            "customer_name": customer,
            "type": kot_type,
            "invoice": invoice_id,
            "pos_profile": pos_profile_id,
            "comments": comments,
            "production": None,  # Cancel KOTs don't have specific production
            "aggregator_id": pos_invoice.custom_aggregator_id,
            "is_aggregator": is_aggregator,
            "order_no": order_number
        }
    )

    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    branch = pos_profile.branch
    if restaurant_table:
        room = frappe.db.get_value("Table", restaurant_table, "restaurant_room")
        restaurant = frappe.db.get_value("Table", restaurant_table, "restaurant")
        menu = frappe.db.get_value("Menu for Room", {"room": room, "parent": restaurant}, "menu")
    else:
        menu = frappe.db.get_value("URY Restaurant", {"branch": branch}, "active_menu")

    for cancel_item in cancel_items:
        course = frappe.db.get_value("URY Menu Item", {"item": cancel_item["item_code"], "parent": menu}, "course")
        for item in invoice_items:
            if cancel_item["item_code"] == item["item_code"]:
                kot_cancel_doc.append(
                    "kot_items",
                    {
                        "item": cancel_item["item_code"],
                        "item_name": cancel_item["item_name"],
                        "cancelled_qty": abs(int(cancel_item["qty"])),
                        "quantity": item["qty"],
                        "comments": cancel_item["comments"],
                        "course": course
                    },
                )

    kot_cancel_doc.insert()
    kot_cancel_doc.submit()


@frappe.whitelist()
def kot_execute(
    invoice_id,
    customer,
    restaurant_table=None,
    current_items=[],
    previous_items=[],
    comments=None,
):
    """Whitelisted function to handle KOT entry"""
    current_items = load_json(current_items)
    previous_items = load_json(previous_items)
    new_invoice_items_array = create_order_items(previous_items)
    new_order_items_array = create_order_items(current_items)

    final_array = compare_two_array(new_order_items_array, new_order_items_array)
    removed_item = get_removed_items(new_invoice_items_array, new_order_items_array)

    pos_invoice = frappe.get_doc("POS Invoice", invoice_id)
    pos_profile_id = pos_invoice.pos_profile
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    kot_naming_series = pos_profile.custom_kot_naming_series

    if kot_naming_series:
        cancel_kot_naming_series = "CNCL-" + kot_naming_series
    else:
        frappe.throw(
            "KOT Naming Series is mandatory for the auto creation of KOT. Ensure it is configured in the POS Profile: %s"
            % pos_profile.name
        )

    positive_qty_items = [item for item in final_array if int(item["qty"]) > 0]
    negative_qty_items = [item for item in final_array if int(item["qty"]) <= 0]
    total_cancel_items = negative_qty_items + removed_item

    if positive_qty_items:
        process_items_for_kot(
            invoice_id,
            customer,
            restaurant_table,
            positive_qty_items,
            comments,
            pos_profile_id,
            kot_naming_series,
            "New Order",
        )

    if total_cancel_items:
        process_items_for_cancel_kot(
            invoice_id,
            customer,
            restaurant_table,
            total_cancel_items,
            comments,
            pos_profile_id,
            cancel_kot_naming_series,
            "Cancelled",
            new_invoice_items_array,
        )


def compare_two_array(array_1, array_2):
    """Compare two arrays and return the items that are different"""
    final_array = []
    for index, x in enumerate(array_1):
        a = list(
            filter(
                lambda y: y["item_code"] == x["item_code"] and y["qty"] == x["qty"],
                array_2,
            )
        )
        if len(a) == 0:
            b = list(filter(lambda z: z["item_code"] == x["item_code"], array_2))
            for qtb in b:
                x["qty"] = int(x["qty"]) - int(qtb["qty"])
            final_array.append(x)
    return final_array


def get_removed_items(array_1, array_2):
    """Get the items that have been removed from the second array compared to the first array"""
    removed_objects = [
        obj
        for obj in array_1
        if obj["item_code"] not in [x["item_code"] for x in array_2]
    ]
    return removed_objects