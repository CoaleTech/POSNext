# Copyright (c) 2025, Posnext. All rights reserved.
# For license information, please see license.txt

import frappe
import json
from frappe.utils.print_format import print_by_server
from frappe.model.document import Document


class KOT(Document):
    def on_submit(self):
        self.multi_print_kot()
        self.kot_display_realtime()

    def before_submit(self):
        self.user_setting()

    def multi_print_kot(self):
        """Function for printing multiple KOTs."""
        def print_kot(printer, kot_print_format):
            try:
                # Print KOT using a server function (print_by_server)
                print_by_server("KOT", self.name, printer, kot_print_format)
            except Exception as e:
                frappe.log_error(f"KOT Print Error: {e}")

        # Get POS Profile printers
        pos_kot_printers = frappe.get_all(
            "Printer Settings",
            fields=["printer", "kot_print_format", "kot_print"],
            filters={"parent": self.pos_profile, "kot_print": 1, "parenttype": "POS Profile"},
            order_by="idx"
        )

        pos_print_flag = True
        if self.production:
            # Get production unit printers
            production_unit_printers = frappe.get_all(
                "Printer Settings",
                fields=["printer", "kot_print_format", "kot_print", "block_takeaway_kot"],
                filters={"parent": self.production, "kot_print": 1, "parenttype": "Production Unit"},
                order_by="idx"
            )

            # Print in production unit printers
            for printer in production_unit_printers:
                pos_print_flag = False
                if printer.block_takeaway_kot == 1:
                    if self.restaurant_table and self.table_takeaway == 0:
                        print_kot(printer.printer, printer.kot_print_format)
                else:
                    print_kot(printer.printer, printer.kot_print_format)

            # Check if restaurant table is specified and it's not a takeaway order
            if self.restaurant_table and self.table_takeaway == 0:
                # Get room printers
                room = frappe.db.get_value("Table", self.restaurant_table, "restaurant_room")
                if room:
                    room_kot_printers = frappe.get_all(
                        "Printer Settings",
                        fields=["printer", "kot_print_format", "kot_print"],
                        filters={"parent": room, "kot_print": 1, "parenttype": "URY Room"},
                        order_by="idx"
                    )
                    # Print KOT in room
                    for printer in room_kot_printers:
                        pos_print_flag = False
                        print_kot(printer.printer, printer.kot_print_format)

            if pos_print_flag:
                if pos_kot_printers:
                    for printer in pos_kot_printers:
                        print_kot(printer.printer, printer.kot_print_format)

        else:
            if pos_kot_printers:
                for printer in pos_kot_printers:
                    print_kot(printer.printer, printer.kot_print_format)

    def kot_display_realtime(self):
        """Function for displaying KOT-related information in real-time on KDS (Kitchen Display System)"""
        current_branch = self.branch
        production = self.production
        kot_json = json.loads(frappe.as_json(self))

        # Get audio file from POS Profile
        audio_file = frappe.db.get_value("POS Profile", self.pos_profile, "custom_kot_alert_sound")

        # Cache key for last KOT time
        cache_key = f"{current_branch}_{production}_last_kot_time"
        time = frappe.cache().get_value(cache_key)

        # Create KOT channel for real-time updates
        kot_channel = f"kot_update_{current_branch}_{production}"

        # Publish real-time update
        frappe.publish_realtime(
            kot_channel,
            {"kot": kot_json, "audio_file": audio_file, "last_kot_time": time},
        )

        # Update cache with current time
        frappe.cache().set_value(cache_key, self.time)

    def user_setting(self):
        """Set user information"""
        user_doc = frappe.get_doc("User", self.owner)
        self.user = user_doc.full_name