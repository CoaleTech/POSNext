import json
import frappe
from frappe.utils import get_datetime, add_to_date, now


def get_branch_from_pos_profile(pos_profile_id):
    """Get branch from POS Profile"""
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    return pos_profile.branch


@frappe.whitelist()
def serve_kot(name, time):
    """Function to set order status in a KOT document"""
    kot_doc = frappe.get_doc("KOT", name)
    kot_doc.order_status = "Served"
    kot_doc.served_time = time
    kot_doc.save()
    frappe.publish_realtime("kot_update", {"message": "KOT Served", "name": name})


@frappe.whitelist()
def confirm_cancel_kot(name, user):
    """Function to mark it as verified by a user in cancel type KOT"""
    kot_doc = frappe.get_doc("KOT", name)
    kot_doc.verified = 1
    kot_doc.verified_by = user
    kot_doc.save()
    frappe.publish_realtime("kot_update", {"message": "KOT Cancelled", "name": name})


@frappe.whitelist(allow_guest=True)
def get_site_name():
    """Get the site name"""
    return frappe.local.site


@frappe.whitelist()
def kot_list():
    """Get list of KOTs for display"""
    today = frappe.utils.now()
    branch = get_branch_from_pos_profile(frappe.form_dict.get("pos_profile"))

    kot_alert_time = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_warning_time"
    )
    daily_order_number = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_reset_order_number_daily"
    )
    three_hours_ago = frappe.utils.add_to_date(today, hours=-3)
    audio_alert = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_alert"
    )

    production = frappe.form_dict.get("production", "")

    filters = {
        "order_status": "Ready For Prepare",
        "branch": branch,
        "type": ("in", ["New Order", "Order Modified", "Duplicate", "Cancelled", "Partially cancelled"]),
        "docstatus": 1,
        "verified": 0,
        "creation": (">=", three_hours_ago),
    }

    if production:
        filters["production"] = production

    kotList = frappe.get_list(
        "KOT",
        fields=["name"],
        filters=filters,
        order_by="creation desc",
    )

    KOT = []
    for kot in kotList:
        kotdoc = frappe.get_doc("KOT", kot.name)
        kotjson = json.loads(frappe.as_json(kotdoc))
        KOT.append(kotjson)

    return {
        "KOT": KOT,
        "Branch": branch,
        "kot_alert_time": kot_alert_time,
        "audio_alert": audio_alert,
        "daily_order_number": daily_order_number
    }


@frappe.whitelist()
def served_kot_list():
    """Get list of served KOTs"""
    today = frappe.utils.now()
    branch = get_branch_from_pos_profile(frappe.form_dict.get("pos_profile"))

    kot_alert_time = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_warning_time"
    )
    daily_order_number = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_reset_order_number_daily"
    )
    three_hours_ago = frappe.utils.add_to_date(today, hours=-3)
    audio_alert = frappe.db.get_value(
        "POS Profile", {"branch": branch}, "custom_kot_alert"
    )

    production = frappe.form_dict.get("production", "")

    filters = {
        "order_status": "Served",
        "branch": branch,
        "type": ("in", ["New Order", "Order Modified", "Duplicate", "Cancelled", "Partially cancelled"]),
        "docstatus": 1,
        "verified": 0,
        "creation": (">=", three_hours_ago),
    }

    if production:
        filters["production"] = production

    kotList = frappe.get_list(
        "KOT",
        fields=["name"],
        filters=filters,
        order_by="creation desc",
    )

    KOT = []
    for kot in kotList:
        kotdoc = frappe.get_doc("KOT", kot.name)
        kotjson = json.loads(frappe.as_json(kotdoc))
        KOT.append(kotjson)

    return {
        "KOT": KOT,
        "Branch": branch,
        "kot_alert_time": kot_alert_time,
        "audio_alert": audio_alert,
        "daily_order_number": daily_order_number
    }


@frappe.whitelist()
def get_production_units():
    """Get production units for the current branch"""
    branch = get_branch_from_pos_profile(frappe.form_dict.get("pos_profile"))
    production_units = frappe.get_all(
        "Production Unit",
        filters={"branch": branch},
        fields=["name", "production_unit_name"]
    )
    return production_units


@frappe.whitelist()
def update_kot_status(name, status, user=None):
    """Update KOT status"""
    kot_doc = frappe.get_doc("KOT", name)
    kot_doc.order_status = status
    if user:
        kot_doc.verified_by = user
        kot_doc.verified = 1
    kot_doc.save()
    frappe.publish_realtime("kot_update", {"message": f"KOT {status}", "name": name})


@frappe.whitelist()
def get_kot_details(name):
    """Get detailed KOT information"""
    kot_doc = frappe.get_doc("KOT", name)
    return json.loads(frappe.as_json(kot_doc))