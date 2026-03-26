# © 2026 SJR Nebula
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFixSerialLocation(TransactionCase):
    """Tests for the Python layer of stock_barcode_free_serial_location.

    fix_serial_source_location() is called by button_validate() and corrects
    the source location on serial-tracked move lines before Odoo records the
    stock move. This prevents negative stock when an operator picks a serial
    from a location other than the one Odoo originally reserved.

    The JS layer (BarcodePickingModel.createNewLine patch) is not testable
    in Python unit tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search([], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.cust_location = cls.env.ref("stock.stock_location_customers")

        cls.company = cls.warehouse.company_id

        # Two shelf sub-locations: the reserved one and where the item actually is
        cls.loc_reserved = cls.env["stock.location"].create(
            {
                "name": "Test Shelf Reserved",
                "location_id": cls.stock_location.id,
                "usage": "internal",
                "company_id": cls.company.id,
            }
        )
        cls.loc_actual = cls.env["stock.location"].create(
            {
                "name": "Test Shelf Actual",
                "location_id": cls.stock_location.id,
                "usage": "internal",
                "company_id": cls.company.id,
            }
        )

        cls.product_serial = cls.env["product.product"].create(
            {
                "name": "Serial Test Product",
                "detailed_type": "product",
                "tracking": "serial",
                "company_id": cls.company.id,
            }
        )
        cls.product_lot = cls.env["product.product"].create(
            {
                "name": "Lot Test Product",
                "detailed_type": "product",
                "tracking": "lot",
                "company_id": cls.company.id,
            }
        )

    def _make_serial(self, name, product=None):
        return self.env["stock.lot"].create(
            {
                "name": name,
                "product_id": (product or self.product_serial).id,
                "company_id": self.warehouse.company_id.id,
            }
        )

    def _put_stock(self, location, lot, product=None):
        self.env["stock.quant"]._update_available_quantity(
            product or self.product_serial, location, 1, lot_id=lot
        )

    def _create_picking_with_line(self, src_location, lot, product=None, qty_done=1.0):
        """Create a confirmed delivery picking with one move line ready for validate."""
        product = product or self.product_serial
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": src_location.id,
                "location_dest_id": self.cust_location.id,
                "company_id": self.company.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": product.name,
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom_qty": 1.0,
                "product_uom": product.uom_id.id,
                "location_id": src_location.id,
                "location_dest_id": self.cust_location.id,
                "company_id": self.company.id,
            }
        )
        picking.action_confirm()
        move.move_line_ids.unlink()
        self.env["stock.move.line"].create(
            {
                "move_id": move.id,
                "picking_id": picking.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "location_id": src_location.id,
                "location_dest_id": self.cust_location.id,
                "lot_id": lot.id if lot else False,
                "qty_done": qty_done,
                "company_id": self.company.id,
            }
        )
        return picking, move

    # -------------------------------------------------------------------------
    # fix_serial_source_location — unit tests
    # -------------------------------------------------------------------------

    def test_location_corrected_when_serial_at_different_location(self):
        """Quant for serial is at loc_actual; move line shows loc_reserved.
        fix_serial_source_location must update the line to loc_actual.
        """
        sn = self._make_serial("SN-DIFF-001")
        self._put_stock(self.loc_actual, sn)

        _, move = self._create_picking_with_line(self.loc_reserved, sn)
        ml = move.move_line_ids

        ml.fix_serial_source_location()

        self.assertEqual(ml.location_id, self.loc_actual)

    def test_location_unchanged_when_serial_already_at_reserved_location(self):
        """Quant for serial is at loc_reserved — same as the move line. No write."""
        sn = self._make_serial("SN-SAME-001")
        self._put_stock(self.loc_reserved, sn)

        _, move = self._create_picking_with_line(self.loc_reserved, sn)
        ml = move.move_line_ids

        ml.fix_serial_source_location()

        self.assertEqual(ml.location_id, self.loc_reserved)

    def test_location_unchanged_when_serial_not_in_stock(self):
        """No positive quant exists for the serial; location left unchanged, no error."""
        sn = self._make_serial("SN-MISSING-001")
        # No stock added

        _, move = self._create_picking_with_line(self.loc_reserved, sn)
        ml = move.move_line_ids

        ml.fix_serial_source_location()

        self.assertEqual(ml.location_id, self.loc_reserved)

    def test_lot_tracked_line_skipped(self):
        """Lot-tracked lines must not be modified (only serial tracking is handled)."""
        lot = self._make_serial("LOT-001", product=self.product_lot)
        self._put_stock(self.loc_actual, lot, product=self.product_lot)

        _, move = self._create_picking_with_line(
            self.loc_reserved, lot, product=self.product_lot
        )
        ml = move.move_line_ids

        ml.fix_serial_source_location()

        self.assertEqual(ml.location_id, self.loc_reserved)

    def test_line_without_lot_skipped(self):
        """Move line with no lot assigned must not be modified."""
        _, move = self._create_picking_with_line(self.loc_reserved, lot=None)
        ml = move.move_line_ids

        ml.fix_serial_source_location()

        self.assertEqual(ml.location_id, self.loc_reserved)

    def test_multiple_lines_each_corrected_independently(self):
        """Recordset of two lines: one needing correction, one already correct."""
        sn1 = self._make_serial("SN-MULTI-001")
        sn2 = self._make_serial("SN-MULTI-002")
        self._put_stock(self.loc_actual, sn1)  # sn1 is at loc_actual
        self._put_stock(self.loc_reserved, sn2)  # sn2 is already at loc_reserved

        _, move1 = self._create_picking_with_line(self.loc_reserved, sn1)
        _, move2 = self._create_picking_with_line(self.loc_reserved, sn2)
        ml1 = move1.move_line_ids
        ml2 = move2.move_line_ids

        (ml1 | ml2).fix_serial_source_location()

        self.assertEqual(ml1.location_id, self.loc_actual)  # corrected
        self.assertEqual(ml2.location_id, self.loc_reserved)  # unchanged

    # -------------------------------------------------------------------------
    # button_validate — integration tests
    # -------------------------------------------------------------------------

    def test_validate_corrects_location_no_negative_stock(self):
        """Full validate: serial at loc_actual, move line reserved at loc_reserved.
        After validate, the stock move must originate from loc_actual and no
        negative quants must exist.
        """
        sn = self._make_serial("SN-VAL-001")
        self._put_stock(self.loc_actual, sn)

        picking, move = self._create_picking_with_line(self.loc_reserved, sn)
        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(move.move_line_ids.location_id, self.loc_actual)

        negative = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_serial.id),
                ("quantity", "<", 0),
            ]
        )
        self.assertFalse(negative, "No negative stock should exist after validation")

    def test_validate_serial_at_correct_location_no_negative_stock(self):
        """When the serial is already at the reserved location, validate works normally."""
        sn = self._make_serial("SN-CORRECT-001")
        self._put_stock(self.loc_reserved, sn)

        picking, move = self._create_picking_with_line(self.loc_reserved, sn)
        picking.button_validate()

        self.assertEqual(picking.state, "done")
        self.assertEqual(move.move_line_ids.location_id, self.loc_reserved)

        negative = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_serial.id),
                ("quantity", "<", 0),
            ]
        )
        self.assertFalse(negative)

    def test_validate_two_serials_each_corrected_to_actual_location(self):
        """Two reserved lines both showing loc_reserved; each serial physically
        at a different location. Validates the Python correction for the scenario
        where the JS layer has assigned serial C to reserved line A, and serial A
        to reserved line B.

        Both move lines must be corrected to their respective actual locations.
        """
        loc_z = self.env["stock.location"].create(
            {
                "name": "Test Shelf Z",
                "location_id": self.stock_location.id,
                "usage": "internal",
                "company_id": self.company.id,
            }
        )
        sn1 = self._make_serial("SN-TWO-001")
        sn2 = self._make_serial("SN-TWO-002")
        self._put_stock(self.loc_actual, sn1)  # sn1 at loc_actual
        self._put_stock(loc_z, sn2)  # sn2 at loc_z

        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.out_type_id.id,
                "location_id": self.loc_reserved.id,
                "location_dest_id": self.cust_location.id,
                "company_id": self.company.id,
            }
        )
        move = self.env["stock.move"].create(
            {
                "name": self.product_serial.name,
                "picking_id": picking.id,
                "product_id": self.product_serial.id,
                "product_uom_qty": 2.0,
                "product_uom": self.product_serial.uom_id.id,
                "location_id": self.loc_reserved.id,
                "location_dest_id": self.cust_location.id,
                "company_id": self.company.id,
            }
        )
        picking.action_confirm()
        move.move_line_ids.unlink()

        for sn in (sn1, sn2):
            self.env["stock.move.line"].create(
                {
                    "move_id": move.id,
                    "picking_id": picking.id,
                    "product_id": self.product_serial.id,
                    "product_uom_id": self.product_serial.uom_id.id,
                    "location_id": self.loc_reserved.id,
                    "location_dest_id": self.cust_location.id,
                    "lot_id": sn.id,
                    "qty_done": 1.0,
                    "company_id": self.company.id,
                }
            )

        picking.button_validate()

        self.assertEqual(picking.state, "done")

        ml_sn1 = move.move_line_ids.filtered(lambda l: l.lot_id == sn1)
        ml_sn2 = move.move_line_ids.filtered(lambda l: l.lot_id == sn2)
        self.assertEqual(ml_sn1.location_id, self.loc_actual)
        self.assertEqual(ml_sn2.location_id, loc_z)

        negative = self.env["stock.quant"].search(
            [
                ("product_id", "=", self.product_serial.id),
                ("quantity", "<", 0),
            ]
        )
        self.assertFalse(negative)
