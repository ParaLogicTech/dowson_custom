import frappe
from barcode import Code128
from barcode.writer import SVGWriter
from io import BytesIO


def packing_slip_before_print(doc, method, print_settings):
	# Barcode
	doc.barcode_svg = get_barcode_svg(doc.name, module_width=0.3, module_height=13, font_size=0)

	# PO #
	doc.sales_orders = list(set(item.sales_order for item in doc.items if item.get('sales_order')))
	if doc.sales_orders:
		po_nos = frappe.get_all("Sales Order", filters={"name": ["in", doc.sales_orders]}, pluck="po_no")
		doc.po_no = ", ".join(list(set([n for n in po_nos if n])))
	else:
		doc.po_no = ""

	# Batch Details
	for d in doc.items:
		d.update(get_work_order(d.batch_no))


def batch_before_print(doc, method, print_settings):
	doc.barcode_svg = get_barcode_svg(doc.name, module_width=0.4, module_height=23)
	doc.update(get_purchase_receipt(doc.name))
	doc.update(get_work_order(doc.name))


def get_barcode_svg(number, module_width=0.2, module_height=15, font_size=10):
	barcode = Code128(number, writer=SVGWriter())

	barcode_io = BytesIO()
	barcode.write(barcode_io, options={
		"module_width": module_width,
		"module_height": module_height,
		"font_size": font_size,
		"text_distance": 4,
		"quiet_zone": 0,
	})

	barcode_io.seek(0)
	return barcode_io.read().decode('UTF-8')


def get_work_order(batch_no):
	out = frappe._dict()

	if not batch_no:
		return out

	data = frappe.db.sql("""
		select ste.work_order, sle.posting_date, sle.posting_time
		from `tabStock Ledger Entry` sle
		inner join `tabStock Entry` ste on ste.name = sle.voucher_no and sle.voucher_type = 'Stock Entry'
		where sle.batch_no = %s and ifnull(ste.work_order, '') != '' and sle.actual_qty > 0 and ste.purpose = 'Manufacture'
		order by sle.posting_date desc, sle.posting_time desc, sle.creation desc
		limit 1
	""", batch_no, as_dict=1)

	data = data[0] if data else None
	if data:
		out.work_order = data.work_order
		out.production_date = data.posting_date
		out.production_time = data.posting_time
		out.work_order_doc = frappe.get_doc("Work Order", data.work_order)

	return out


def get_purchase_receipt(batch_no):
	out = frappe._dict()

	if not batch_no:
		return out

	data = frappe.db.sql("""
		select prec.name, prec.supplier, prec.supplier_name, prec.posting_date, prec.posting_time, i.purchase_order
		from `tabPurchase Receipt Item` i
		inner join `tabPurchase Receipt` prec on prec.name = i.parent
		where i.batch_no = %s
		order by prec.posting_date desc, prec.posting_time desc, prec.creation desc
		limit 1
	""", batch_no, as_dict=1)

	data = data[0] if data else None
	if data:
		out.purchase_receipt = data.name
		out.purchase_order = data.purchase_order
		out.supplier = data.supplier
		out.supplier_name = data.supplier_name
		out.received_date = data.posting_date
		out.received_time = data.posting_time

	return out
