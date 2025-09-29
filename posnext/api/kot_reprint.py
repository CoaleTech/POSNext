import frappe
import json
from datetime import datetime, timedelta


def get_branch_from_pos_profile(pos_profile_id):
    """Get branch from POS Profile"""
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    return pos_profile.branch


@frappe.whitelist()
def get_kot_for_reprint(invoice_id=None, kot_name=None):
    """Get KOT details for reprinting"""
    try:
        if kot_name:
            # Get specific KOT
            kot_doc = frappe.get_doc("KOT", kot_name)
        elif invoice_id:
            # Get latest KOT for invoice
            kot_list = frappe.get_all(
                "KOT",
                filters={"invoice": invoice_id, "docstatus": 1},
                fields=["name"],
                order_by="creation desc",
                limit=1
            )
            if not kot_list:
                return {"error": "No KOT found for this invoice"}
            kot_doc = frappe.get_doc("KOT", kot_list[0].name)
        else:
            return {"error": "Either invoice_id or kot_name must be provided"}

        return json.loads(frappe.as_json(kot_doc))

    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def reprint_kot(kot_name, printer_level="pos_profile"):
    """Reprint a KOT"""
    try:
        kot_doc = frappe.get_doc("KOT", kot_name)

        # Get printer settings from POS Profile
        pos_profile = frappe.get_doc("POS Profile", kot_doc.pos_profile)

        printer_ip = None
        if printer_level == "pos_profile":
            printer_ip = pos_profile.printer
        elif printer_level == "production_unit" and kot_doc.production:
            # Get printer from production unit
            production_unit = frappe.get_doc("Production Unit", kot_doc.production)
            printer_ip = production_unit.printer
        elif printer_level == "room":
            # Get printer from room (if table is assigned)
            if kot_doc.restaurant_table:
                room = frappe.db.get_value("Table", kot_doc.restaurant_table, "restaurant_room")
                if room:
                    room_doc = frappe.get_doc("URY Room", room)
                    printer_ip = room_doc.printer

        if not printer_ip:
            return {"error": f"No printer configured for {printer_level} level"}

        # Trigger print (this would integrate with your printing system)
        print_result = kot_doc.multi_print_kot(printer_ip, printer_level)

        # Log the reprint action
        frappe.get_doc({
            "doctype": "KOT Print Log",
            "kot": kot_name,
            "printer": printer_ip,
            "print_level": printer_level,
            "action": "reprint",
            "printed_by": frappe.session.user
        }).insert()

        return {"success": True, "message": "KOT reprinted successfully", "printer": printer_ip}

    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def get_recent_kots(pos_profile_id, limit=10):
    """Get recent KOTs for reprint options"""
    try:
        branch = get_branch_from_pos_profile(pos_profile_id)

        # Get KOTs from last 24 hours
        yesterday = datetime.now() - timedelta(days=1)

        kots = frappe.get_all(
            "KOT",
            filters={
                "branch": branch,
                "docstatus": 1,
                "creation": (">=", yesterday)
            },
            fields=["name", "invoice", "restaurant_table", "customer_name", "type", "creation", "order_status"],
            order_by="creation desc",
            limit=limit
        )

        return kots

    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def bulk_reprint_kots(kot_names, printer_level="pos_profile"):
    """Reprint multiple KOTs"""
    try:
        results = []
        for kot_name in kot_names:
            result = reprint_kot(kot_name, printer_level)
            results.append({
                "kot_name": kot_name,
                "success": "success" in result,
                "message": result.get("message", result.get("error", "Unknown error"))
            })

        successful = sum(1 for r in results if r["success"])
        return {
            "results": results,
            "summary": f"{successful}/{len(kot_names)} KOTs reprinted successfully"
        }

    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def get_kot_print_history(kot_name=None, date_from=None, date_to=None, limit=50):
    """Get KOT print history"""
    try:
        filters = {}

        if kot_name:
            filters["kot"] = kot_name

        if date_from and date_to:
            filters["creation"] = ["between", [date_from, date_to]]

        print_history = frappe.get_all(
            "KOT Print Log",
            filters=filters,
            fields=["name", "kot", "printer", "print_level", "action", "printed_by", "creation"],
            order_by="creation desc",
            limit=limit
        )

        return print_history

    except Exception as e:
        return {"error": str(e)}