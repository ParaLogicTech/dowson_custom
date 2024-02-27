import frappe
from barcode import Code128
from barcode.writer import SVGWriter
from io import BytesIO


def batch_before_print(doc, method, print_settings):
	get_barcode_svg(doc)
	get_work_order(doc)


def get_barcode_svg(doc):
	barcode = Code128(doc.name, writer=SVGWriter())

	barcode_io = BytesIO()
	barcode.write(barcode_io, options={
		"module_width": 0.4,
		"module_height": 23,
		"text_distance": 4,
		"quiet_zone": 0,
	})

	barcode_io.seek(0)
	doc.barcode_svg = barcode_io.read().decode('UTF-8')


def get_work_order(doc):
	data = frappe.db.sql("""
		select ste.work_order, sle.posting_date, sle.posting_time
		from `tabStock Ledger Entry` sle
		inner join `tabStock Entry` ste on ste.name = sle.voucher_no and sle.voucher_type = 'Stock Entry'
		where sle.batch_no = %s and ifnull(ste.work_order, '') != '' and sle.actual_qty > 0
		order by sle.posting_date desc, sle.posting_time desc, sle.creation desc
		limit 1
	""", doc.name, as_dict=1)

	data = data[0] if data else None
	if data:
		doc.work_order = data.work_order
		doc.production_date = data.posting_date
		doc.production_time = data.posting_time

		doc.work_order_doc = frappe.get_doc("Work Order", doc.work_order)
