from frappe import _


def get_data():
	return [
		{
			"label": _("POSNext"),
			"icon": "fa fa-shopping-cart",
			"items": [
				{
					"type": "page",
					"name": "posnext",
					"description": _("Point of Sale Next Generation"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "KOT",
					"description": _("Kitchen Order Ticket"),
				},
				{
					"type": "doctype",
					"name": "Production Unit",
					"description": _("Production Unit for KOT"),
				},
				{
					"type": "doctype",
					"name": "Printer Setting",
					"description": _("Printer Settings for KOT"),
				},
			],
		},
	]