import frappe


def create_kot_custom_fields():
    """Create custom fields required for KOT functionality"""
    
    # Custom fields for POS Profile
    pos_profile_fields = [
        {
            'fieldname': 'custom_kot_settings',
            'fieldtype': 'Section Break',
            'label': 'KOT Settings',
            'insert_after': 'print_format_for_online'
        },
        {
            'fieldname': 'custom_kot_naming_series',
            'fieldtype': 'Select',
            'label': 'KOT Naming Series',
            'options': 'KOT-{YYYY}-{MM}-{DD}-{#####}\nKOT-{#####}\nKOT-{YY}-{MM}-{#####}',
            'insert_after': 'custom_kot_settings',
            'description': 'Naming series for Kitchen Order Tickets'
        },
        {
            'fieldname': 'custom_kot_alert',
            'fieldtype': 'Check',
            'label': 'Enable KOT Alert',
            'insert_after': 'custom_kot_naming_series',
            'description': 'Enable audio/visual alerts for KOT preparation time'
        },
        {
            'fieldname': 'custom_kot_warning_time',
            'fieldtype': 'Int',
            'label': 'KOT Warning Time (minutes)',
            'insert_after': 'custom_kot_alert',
            'default': '15',
            'description': 'Time after which KOT shows warning if not prepared'
        },
        {
            'fieldname': 'custom_reset_order_number_daily',
            'fieldtype': 'Check',
            'label': 'Reset Order Number Daily',
            'insert_after': 'custom_kot_warning_time',
            'description': 'Reset order numbers daily'
        }
    ]
    
    # Custom fields for POS Invoice
    pos_invoice_fields = [
        {
            'fieldname': 'custom_restaurant_table',
            'fieldtype': 'Link',
            'label': 'Restaurant Table',
            'options': 'Table',
            'insert_after': 'customer',
            'description': 'Selected table for this order'
        },
        {
            'fieldname': 'custom_comments',
            'fieldtype': 'Text',
            'label': 'Order Comments',
            'insert_after': 'custom_restaurant_table',
            'description': 'Special instructions or comments for the order'
        }
    ]

    # Custom fields for POS Invoice Item
    pos_invoice_item_fields = [
        {
            'fieldname': 'custom_comments',
            'fieldtype': 'Text',
            'label': 'Item Comments',
            'insert_after': 'description',
            'description': 'Special instructions for this item'
        }
    ]
    
    # Create custom fields
    create_custom_fields_for_doctype('POS Profile', pos_profile_fields)
    create_custom_fields_for_doctype('POS Invoice', pos_invoice_fields)
    create_custom_fields_for_doctype('POS Invoice Item', pos_invoice_item_fields)


def create_custom_fields_for_doctype(doctype, fields):
    """Create custom fields for a specific doctype"""
    for field in fields:
        field_name = f"{doctype}-{field['fieldname']}"
        
        # Check if field already exists
        if not frappe.db.exists('Custom Field', field_name):
            custom_field = frappe.get_doc({
                'doctype': 'Custom Field',
                'dt': doctype,
                **field
            })
            custom_field.insert()
            print(f"Created custom field: {field_name}")
        else:
            print(f"Custom field already exists: {field_name}")


def execute():
    """Execute the custom field creation"""
    create_kot_custom_fields()
    frappe.db.commit()
    print("KOT custom fields created successfully!")