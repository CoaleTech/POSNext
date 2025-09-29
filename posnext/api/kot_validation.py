import frappe
import json
from datetime import datetime, timedelta


def get_branch_from_pos_profile(pos_profile_id):
    """Get branch from POS Profile"""
    pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
    return pos_profile.branch


def get_productions_for_branch(branch):
    """Get production units for a given branch"""
    return frappe.get_all(
        "Production Unit",
        filters={"branch": branch},
        fields=["name", "production_unit_name"]
    )


@frappe.whitelist()
def validate_kot_generation(invoice_id, pos_profile_id):
    """Validate if KOT can be generated for the invoice"""
    try:
        # Check if POS Profile has KOT naming series
        pos_profile = frappe.get_doc("POS Profile", pos_profile_id)
        if not pos_profile.custom_kot_naming_series:
            return {
                "valid": False,
                "message": "KOT Naming Series is mandatory for KOT generation. Please configure it in POS Profile."
            }

        # Check if production units exist for the branch
        branch = pos_profile.branch
        productions = get_productions_for_branch(branch)
        if not productions:
            return {
                "valid": False,
                "message": f"No Production Units found for branch {branch}. Please create Production Units."
            }

        # Check if invoice exists and is valid
        invoice = frappe.get_doc("POS Invoice", invoice_id)
        if invoice.docstatus != 1:
            return {
                "valid": False,
                "message": "Invoice must be submitted before generating KOT."
            }

        return {"valid": True, "message": "Validation successful"}

    except Exception as e:
        return {"valid": False, "message": str(e)}


@frappe.whitelist()
def validate_printer_settings(pos_profile_id):
    """Validate printer settings for KOT printing"""
    try:
        pos_profile = frappe.get_doc("POS Profile", pos_profile_id)

        # Check if printer settings exist
        if not hasattr(pos_profile, 'printer_settings') or not pos_profile.printer_settings:
            return {
                "valid": False,
                "message": "No printer settings configured in POS Profile."
            }

        # Validate each printer setting
        for printer_setting in pos_profile.printer_settings:
            if not printer_setting.printer:
                return {
                    "valid": False,
                    "message": f"Printer not configured for {printer_setting.level} level."
                }

        return {"valid": True, "message": "Printer settings validated"}

    except Exception as e:
        return {"valid": False, "message": str(e)}


@frappe.whitelist()
def check_kot_status(kot_name):
    """Check the current status of a KOT"""
    try:
        kot = frappe.get_doc("KOT", kot_name)
        return {
            "status": kot.order_status,
            "verified": kot.verified,
            "verified_by": kot.verified_by,
            "served_time": kot.served_time
        }
    except Exception as e:
        return {"error": str(e)}


@frappe.whitelist()
def validate_item_groups_for_production(branch):
    """Validate that all items have proper item groups assigned to production units"""
    try:
        # Get all items
        items = frappe.get_all("Item", fields=["name", "item_group"])

        # Get all production units for branch
        productions = get_productions_for_branch(branch)

        # Get all item groups assigned to production units
        production_item_groups = set()
        for production in productions:
            production_doc = frappe.get_doc("Production Unit", production.name)
            for item_group in production_doc.item_groups:
                production_item_groups.add(item_group.item_group)

        # Check for items not assigned to any production unit
        unassigned_items = []
        for item in items:
            if item.item_group not in production_item_groups:
                unassigned_items.append({
                    "item_code": item.name,
                    "item_group": item.item_group
                })

        if unassigned_items:
            return {
                "valid": False,
                "message": f"Following items are not assigned to any production unit: {', '.join([item['item_code'] for item in unassigned_items])}",
                "unassigned_items": unassigned_items
            }

        return {"valid": True, "message": "All items are properly assigned"}

    except Exception as e:
        return {"valid": False, "message": str(e)}


@frappe.whitelist()
def get_kot_statistics(branch, date_from=None, date_to=None):
    """Get KOT statistics for reporting"""
    try:
        filters = {"branch": branch, "docstatus": 1}

        if date_from and date_to:
            filters["creation"] = ["between", [date_from, date_to]]

        # Get total KOTs
        total_kots = frappe.db.count("KOT", filters=filters)

        # Get KOTs by status
        status_stats = frappe.db.get_all(
            "KOT",
            filters=filters,
            fields=["order_status", "count(*) as count"],
            group_by="order_status"
        )

        # Get KOTs by type
        type_stats = frappe.db.get_all(
            "KOT",
            filters=filters,
            fields=["type", "count(*) as count"],
            group_by="type"
        )

        return {
            "total_kots": total_kots,
            "status_breakdown": status_stats,
            "type_breakdown": type_stats
        }

    except Exception as e:
        return {"error": str(e)}