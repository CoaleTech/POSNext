frappe.provide('posnext.PointOfSale');

posnext.PointOfSale.TableSelector = class {
	constructor({ wrapper, events, settings }) {
		console.log('TableSelector constructor called');
		this.wrapper = wrapper;
		this.events = events;
		this.settings = settings;
		this.selected_table = null;
		this.init_component();
	}

	init_component() {
		this.prepare_dom();
		this.load_tables_data();
		this.bind_events();
		// Add table selection mode to body
		$('body').addClass('table-selection-mode');
	}

	prepare_dom() {
		this.$component = $(`
			<div class="table-selection-page">
				<div class="table-selector-container">
					<div class="table-selector-section">
						<div class="table-selector-header">
							<h4 class="section-title">
								<i class="fa fa-utensils"></i>
								Select Table
							</h4>
							<p class="section-subtitle">Choose a table to start your order</p>
						</div>
						<div class="table-grid">
							<!-- Tables will be loaded here -->
						</div>
						<div class="table-selector-footer">
							<button class="btn btn-primary btn-lg proceed-btn">
								<i class="fa fa-arrow-right"></i>
								Proceed to Order
							</button>
						</div>
					</div>
				</div>
			</div>
		`).appendTo('body');

		this.$table_grid = this.$component.find('.table-grid');
		this.$proceed_btn = this.$component.find('.proceed-btn');
	}

	load_tables_data() {
		console.log('Loading tables data...');
		// First get all tables
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Table',
				fields: ['name', 'table_number', 'capacity', 'status', 'description'],
				limit_page_length: 100
			},
			callback: (r) => {
				console.log('Tables data received:', r);
				if (r.message) {
					// Check for active orders for each table
					this.check_active_orders(r.message);
				} else {
					console.log('No tables data received');
					this.$table_grid.html('<p class="text-center">No tables available</p>');
				}
			},
			error: (r) => {
				console.error('Error loading tables:', r);
				this.$table_grid.html('<p class="text-center text-danger">Error loading tables</p>');
			}
		});
	}

	check_active_orders(tables) {
		// Get all active POS invoices with table assignments
		frappe.call({
			method: 'frappe.client.get_list',
			args: {
				doctype: 'Sales Invoice',
				fields: ['name', 'custom_restaurant_table', 'docstatus'],
				filters: {
					docstatus: 0, // Draft invoices (active orders)
					custom_restaurant_table: ['!=', ''],
					is_pos: 1
				},
				limit_page_length: 1000
			},
			callback: (r) => {
				const activeOrders = r.message || [];
				const occupiedTables = new Set(activeOrders.map(order => order.custom_restaurant_table));

				// Update table status based on active orders
				tables.forEach(table => {
					if (occupiedTables.has(table.name)) {
						table.status = 'Occupied';
					} else {
						table.status = 'Available';
					}
				});

				this.render_tables(tables);
			},
			error: (r) => {
				console.error('Error checking active orders:', r);
				// Still render tables even if order check fails
				this.render_tables(tables);
			}
		});
	}

	render_tables(tables) {
		console.log('Rendering tables:', tables);
		this.$table_grid.empty();

		if (tables.length === 0) {
			this.$table_grid.html('<p class="text-center">No tables available</p>');
			return;
		}

		tables.forEach(table => {
			const table_card = $(`
				<div class="table-card ${table.status.toLowerCase()} ${this.selected_table === table.name ? 'selected' : ''}"
					 data-table="${table.name}">
					<div class="table-number">${table.table_number}</div>
					<div class="table-info">
						<div class="capacity">Capacity: ${table.capacity}</div>
						<div class="status">${table.status}</div>
					</div>
					${table.description ? `<div class="description">${table.description}</div>` : ''}
				</div>
			`);
			this.$table_grid.append(table_card);
		});
	}

	bind_events() {
		const me = this;

		this.$table_grid.on('click', '.table-card', function() {
			const $card = $(this);
			const table_name = $card.data('table');

			// Check if table is occupied
			if ($card.hasClass('occupied')) {
				frappe.msgprint(__('This table is currently occupied. Please select an available table.'));
				return;
			}

			// Remove selected class from all cards
			me.$table_grid.find('.table-card').removeClass('selected');

			// Add selected class to clicked card
			$card.addClass('selected');

			me.selected_table = table_name;
			me.events.table_selected(table_name);
		});

		this.$proceed_btn.on('click', () => {
			if (this.selected_table) {
				this.events.proceed_to_items();
			} else {
				frappe.msgprint(__('Please select a table first'));
			}
		});
	}

	toggle_component(show) {
		this.$component.toggle(show);
		// When hiding table selector, restore original POS layout
		if (!show) {
			$('body').removeClass('table-selection-mode');
		} else {
			$('body').addClass('table-selection-mode');
			// Reload table data to get latest status when component becomes visible
			this.load_tables_data();
		}
	}
};