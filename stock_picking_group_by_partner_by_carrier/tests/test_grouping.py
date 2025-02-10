# Copyright 2020 Camptocamp (https://www.camptocamp.com)
# Copyright 2020 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.fields import first
from odoo.tests import Form
from odoo.tests.common import TransactionCase

from .common import TestGroupByBase


class TestGroupBy(TestGroupByBase, TransactionCase):
    def test_sale_stock_merge_same_partner_no_carrier(self):
        """2 sale orders for the same partner, without carrier

        -> the pickings are merged"""
        so1 = self._get_new_sale_order()
        so2 = self._get_new_sale_order(amount=11)
        so1.action_confirm()
        so2.action_confirm()
        self.assertTrue(so1.picking_ids)
        self.assertEqual(so1.picking_ids, so2.picking_ids)

    def test_sale_stock_merge_same_carrier(self):
        """2 sale orders for the same partner, with same carrier

        -> the pickings are merged"""
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so1.action_confirm()
        so2.action_confirm()
        # there is a picking for the sales, and it is shared
        self.assertTrue(so1.picking_ids)
        self.assertEqual(so1.picking_ids, so2.picking_ids)
        # the origin of the picking mentions both sales names
        self.assertTrue(so1.name in so1.picking_ids[0].origin)
        self.assertTrue(so2.name in so1.picking_ids[0].origin)

    def test_sale_stock_no_merge_different_carrier(self):
        """2 sale orders for the same partner, with different carriers

        -> the pickings are not merged"""
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier2)
        so1.action_confirm()
        so2.action_confirm()
        self.assertEqual(so1.picking_ids.carrier_id, self.carrier1)
        self.assertEqual(so2.picking_ids.carrier_id, self.carrier2)
        self.assertNotEqual(so1.picking_ids, so2.picking_ids)
        self.assertTrue(so1.name in so1.picking_ids[0].origin)
        self.assertTrue(so2.name in so2.picking_ids[0].origin)

    def test_sale_stock_no_merge_carrier_set_only_on_one(self):
        """2 sale orders for the same partner, one with the other without

        -> the pickings are not merged"""
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so2 = self._get_new_sale_order(amount=11, carrier=None)
        so1.action_confirm()
        so2.action_confirm()
        self.assertEqual(so1.picking_ids.carrier_id, self.carrier1)
        self.assertFalse(so2.picking_ids.carrier_id)
        self.assertNotEqual(so1.picking_ids, so2.picking_ids)

    def test_sale_stock_no_merge_same_carrier_picking_policy_one(self):
        """2 sale orders for the same partner, with same carrier, deliver at
        once picking policy

        -> the pickings are not merged

        """
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.picking_policy = "one"
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.picking_policy = "one"
        so1.action_confirm()
        so2.action_confirm()
        # there is a picking for each the sales, different
        self.assertTrue(so1.picking_ids)
        self.assertTrue(so2.picking_ids)
        self.assertNotEqual(so1.picking_ids, so2.picking_ids)
        # the origin of the picking mentions both sales names
        self.assertTrue(so1.name in so1.picking_ids[0].origin)
        self.assertTrue(so2.name in so2.picking_ids[0].origin)

    def test_sale_stock_no_merge_same_carrier_mixed_picking_policy(self):
        """2 sale orders for the same partner, with same carrier, deliver at once
        picking policy for the 1st sale order.

        -> the pickings are not merged

        """
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.picking_policy = "one"
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so1.action_confirm()
        so2.action_confirm()
        # there is a picking for each the sales, different
        self.assertTrue(so1.picking_ids)
        self.assertTrue(so2.picking_ids)
        self.assertNotEqual(so1.picking_ids, so2.picking_ids)
        # the origin of the picking mentions both sales names
        self.assertTrue(so1.name in so1.picking_ids[0].origin)
        self.assertTrue(so2.name in so2.picking_ids[0].origin)

    def test_printed_pick_no_merge(self):
        """1st sale order ship is printed, 2nd sale order not merged"""
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        so1.picking_ids.do_print_picking()
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        self.assertNotEqual(so1.picking_ids, so2.picking_ids)

    def test_backorder_picking_merge(self):
        """1st sale order ship is printed, 2nd sale order not merged.
        Partial delivery of so1

        -> backorder is merged with so2 picking

        """
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        so1.picking_ids.do_print_picking()
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        pick = so1.picking_ids
        move = first(pick.move_ids)
        move.quantity = 5
        move.picked = True
        print("----- Test backorder -----")
        pick.with_context(cancel_backorder=False)._action_done()
        so2.invalidate_recordset()
        print("---Test so1.picking_ids", so1.picking_ids)
        print("---Test so2.picking_ids", so2.picking_ids)
        self.assertTrue(so2.picking_ids & so1.picking_ids)
        self.assertEqual(so2.picking_ids.sale_ids, so1 + so2)

    def test_cancelling_sale_order1(self):
        """1st sale order is cancelled

        -> picking is still todo with only 1 stock move todo"""
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        self.assertTrue(so1.picking_ids)
        self.assertTrue(so2.picking_ids)
        self.assertEqual(so1.picking_ids, so2.picking_ids)
        so1._action_cancel()
        self.assertNotEqual(so1.picking_ids.state, "cancel")
        moves = so1.picking_ids.move_ids
        so1_moves = moves.filtered(lambda m: m.sale_line_id.order_id == so1)
        so2_moves = moves.filtered(lambda m: m.sale_line_id.order_id == so2)
        self.assertEqual(so1_moves.mapped("state"), ["cancel"])
        self.assertEqual(so2_moves.mapped("state"), ["confirmed"])
        self.assertEqual(so1.state, "cancel")
        self.assertEqual(so2.state, "sale")

    def test_cancelling_sale_order1_before_create_order2(self):
        """1st sale order is cancelled

        -> picking is still todo with only 1 stock move todo"""
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        so1._action_cancel()
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        self.assertTrue(so1.picking_ids)
        self.assertTrue(so2.picking_ids)
        self.assertFalse(so1.picking_ids & so2.picking_ids)

    def test_cancelling_sale_order2(self):
        """2nd sale order is cancelled

        -> picking is still todo with only 1 stock move todo"""
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        self.assertTrue(so1.picking_ids)
        self.assertTrue(so2.picking_ids)
        self.assertEqual(so1.picking_ids, so2.picking_ids)
        so2._action_cancel()
        self.assertNotEqual(so1.picking_ids.state, "cancel")
        moves = so1.picking_ids.move_ids
        so1_moves = moves.filtered(lambda m: m.sale_line_id.order_id == so1)
        so2_moves = moves.filtered(lambda m: m.sale_line_id.order_id == so2)
        self.assertEqual(so1_moves.mapped("state"), ["confirmed"])
        self.assertEqual(so2_moves.mapped("state"), ["cancel"])
        self.assertEqual(so1.state, "sale")
        self.assertEqual(so2.state, "cancel")

    def test_delivery_multi_step(self):
        """the warehouse uses pick + ship

        -> shippings are grouped, pickings are not"""
        print("----- Test test_delivery_multi_step -----")
        self.warehouse.delivery_steps = "pick_ship"

        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        self.assertEqual(len(so1.picking_ids), 1)

        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        self.assertEqual(len(so2.picking_ids), 1)

        # the ship will be create after validation of the pick
        move = first(so1.picking_ids.move_ids)
        move.quantity = 10
        so1.picking_ids.button_validate()

        move = first(so2.picking_ids.move_ids)
        move.quantity = 11
        so2.picking_ids.button_validate()

        self.assertEqual(len(so1.picking_ids), 2)
        self.assertEqual(len(so2.picking_ids), 2)

        # ship should be shared between so1 and so2
        ships = (so1.picking_ids | so2.picking_ids).filtered(
            lambda p: p.picking_type_code == "outgoing"
        )
        self.assertEqual(len(ships), 1)
        self.assertEqual(ships.picking_type_id, self.warehouse.out_type_id)
        # but not picks
        # Note: When grouping the ships, all pulled internal moves should also
        # be regrouped but this is currently not supported by this module. You
        # need the stock_available_to_promise_release module to have this
        # feature
        picks = so1.picking_ids - ships
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks.picking_type_id, self.warehouse.pick_type_id)
        # the group is the same on the move lines and shipping
        self.assertEqual(len(ships.group_id), 1)
        self.assertEqual(ships.group_id, ships.move_ids.group_id)
        # Add a line to so1
        self.assertEqual(len(ships.move_ids), 2)
        sale_form = Form(so1)
        self._set_line(sale_form, 4)
        sale_form.save()
        picks = so1.picking_ids.filtered(lambda p: p.state != "done") - ships
        move = picks.move_ids[-1]
        move.quantity = 10
        picks.button_validate()
        self.assertEqual(len(ships.move_ids), 3)
        # the group is the same on the move lines and picking
        self.assertEqual(len(ships.group_id), 1)
        self.assertEqual(ships.group_id, ships.move_ids.group_id)
        # Add a line to so2
        self.assertEqual(len(ships.move_ids), 3)
        sale_form = Form(so2)
        self._set_line(sale_form, 4)
        sale_form.save()
        picks = so2.picking_ids.filtered(lambda p: p.state != "done") - ships
        move = picks.move_ids[-1]
        move.quantity = 10
        picks.button_validate()
        self.assertEqual(len(ships.move_ids), 4)
        # the group is the same on the move lines and picking
        self.assertEqual(len(ships.group_id), 1)
        self.assertEqual(ships.group_id, ships.move_ids.group_id)

    def test_delivery_multi_step_cancel_so1(self):
        """the warehouse uses pick + ship. Cancel SO1

        -> shippings are grouped, pickings are not"""
        print("----- test_grouping test_delivery_multi_step_cancel_so1 -----")
        self.warehouse.delivery_steps = "pick_ship"
        rule = self.env["procurement.group"]._get_rule(
            self.product,
            self.partner.property_stock_customer,
            {"warehouse_id": self.warehouse},
        )
        rule.propagate_carrier = False
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        move = first(so1.picking_ids.move_ids)
        move.quantity = 10
        so1.picking_ids.button_validate()

        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        move = first(so2.picking_ids.move_ids)
        move.quantity = 11
        so2.picking_ids.button_validate()

        so1._action_cancel()

        ships = (so1.picking_ids | so2.picking_ids).filtered(
            lambda p: p.picking_type_code == "outgoing"
        )
        pick1 = so1.picking_ids.filtered(
            lambda o: o.picking_type_id == self.warehouse.pick_type_id
        )
        pick2 = so2.picking_ids.filtered(
            lambda o: o.picking_type_id == self.warehouse.pick_type_id
        )
        self.assertEqual(ships.state, "assigned")
        self.assertEqual(pick1.state, "done")
        self.assertEqual(pick2.state, "done")
        self.assertEqual(ships.move_ids[0].quantity, 0)

    def test_delivery_multi_step_cancel_so2(self):
        """the warehouse uses pick + ship. Cancel SO2

        -> shippings are grouped, pickings are not"""
        print("----- test_grouping test_delivery_multi_step_cancel_so2 -----")
        self.warehouse.delivery_steps = "pick_ship"
        rule = self.env["procurement.group"]._get_rule(
            self.product,
            self.partner.property_stock_customer,
            {"warehouse_id": self.warehouse},
        )
        rule.propagate_carrier = False
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        move = first(so1.picking_ids.move_ids)
        move.quantity = 10
        so1.picking_ids.button_validate()

        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        move = first(so2.picking_ids.move_ids)
        move.quantity = 11
        so2.picking_ids.button_validate()

        so2._action_cancel()

        ships = (so1.picking_ids | so2.picking_ids).filtered(
            lambda p: p.picking_type_code == "outgoing"
        )
        pick1 = so1.picking_ids.filtered(
            lambda o: o.picking_type_id == self.warehouse.pick_type_id
        )
        pick2 = so2.picking_ids.filtered(
            lambda o: o.picking_type_id == self.warehouse.pick_type_id
        )

        self.assertEqual(ships.state, "assigned")
        self.assertEqual(pick1.state, "done")
        self.assertEqual(pick2.state, "done")
        self.assertEqual(ships.move_ids[1].quantity, 0)

    def test_delivery_multi_step_cancel_so1_create_so3(self):
        """the warehouse uses pick + ship. Cancel SO1, create SO3

        -> shippings are grouped, pickings are not"""
        print(
            "----- test_grouping test_delivery_multi_step_cancel_so1_create_so3 -----"
        )
        self.warehouse.delivery_steps = "pick_ship"
        rule = self.env["procurement.group"]._get_rule(
            self.product,
            self.partner.property_stock_customer,
            {"warehouse_id": self.warehouse},
        )
        rule.propagate_carrier = False
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        move = first(so1.picking_ids.move_ids)
        move.quantity = 10
        so1.picking_ids.button_validate()

        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        move = first(so2.picking_ids.move_ids)
        move.quantity = 11
        so2.picking_ids.button_validate()

        ships = (so1.picking_ids | so2.picking_ids).filtered(
            lambda p: p.picking_type_code == "outgoing"
        )
        so1._action_cancel()
        so3 = self._get_new_sale_order(amount=12, carrier=self.carrier1)
        so3.action_confirm()
        move = first(so3.picking_ids.move_ids)
        move.quantity = 12
        so3.picking_ids.button_validate()

        self.assertTrue(ships in so3.picking_ids)
        pick3 = so3.picking_ids.filtered(
            lambda o: o.picking_type_id == self.warehouse.pick_type_id
        )
        self.assertEqual(len(pick3), 1)
        self.assertEqual(pick3.state, "done")

    def test_delivery_mult_step_cancelling_sale_order1_before_create_order2(self):
        """1st sale order is cancelled

        -> picking is still todo with only 1 stock move todo"""
        print(
            "----- test_grouping test_delivery_mult_step_cancelling_sale_order1_before_create_order2 -----"
        )
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.action_confirm()
        move = first(so1.picking_ids.move_ids)
        move.quantity = 10
        so1.picking_ids.button_validate()
        so1._action_cancel()

        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.action_confirm()
        move = first(so2.picking_ids.move_ids)
        move.quantity = 11
        so2.picking_ids.button_validate()

        self.assertTrue(so1.picking_ids)
        self.assertTrue(so2.picking_ids)
        self.assertFalse(so1.picking_ids & so2.picking_ids)

    def test_sale_stock_merge_procurement_group(self):
        """sales orders moves are merged, procurement groups are merged

        Ensure that the procurement group is linked with both SO
        and we find the stock.picking records from the SO.
        Ensure that printed transfers keep their procurement group.
        """
        print("----- test_grouping test_sale_stock_merge_procurement_group -----")
        so1 = self._get_new_sale_order(carrier=self.carrier1)
        so1.name = "SO1"
        so2 = self._get_new_sale_order(amount=11, carrier=self.carrier1)
        so2.name = "SO2"
        so1.action_confirm()
        so2.action_confirm()
        self.assertEqual(so1.picking_ids, so2.picking_ids)
        picking = so1.picking_ids
        # the group is the same on the move lines and picking
        self.assertEqual(picking.group_id, picking.move_ids.group_id)
        group = picking.group_id
        # the group is related to both sales orders
        print("---group.sale_ids", group.sale_ids)
        self.assertEqual(group.sale_ids, so1 | so2)
        self.assertEqual(group.name, "Merged procurement for partners: Test Partner")

        line = so1.order_line.filtered(lambda line: not line.is_delivery)

        self._update_qty_in_location(
            picking.location_id,
            line.product_id,
            line.product_uom_qty,
        )
        picking.action_assign()

        # process move of so1, we'll expect groups for new backorders and new
        # transfers merged in the backorder to "forget" about so1
        move1 = picking.move_ids.filtered(
            lambda line: line.sale_line_id.order_id == so1
        )
        line1 = move1.move_line_ids
        line1.quantity = line1.quantity_product_uom
        print("---Test picking:", picking)
        picking._action_done()
        print("---Test picking:", picking)

        backorder = picking.backorder_ids

        so3 = self._get_new_sale_order(carrier=self.carrier1)
        so3.name = "SO3"
        so3.action_confirm()

        # so3 moves are merged in the backorder used for so2,
        # a new group is used to hold so2 and so3
        self.assertEqual(backorder.group_id.sale_ids, so2 | so3)
        self.assertEqual(
            backorder.group_id.name, "Merged procurement for partners: Test Partner"
        )

        self.assertEqual(so1.picking_ids, picking)
        self.assertEqual(so2.picking_ids, picking | backorder)
        self.assertEqual(so3.picking_ids, backorder)

    def test_create_backorder(self):
        """Ensure there is no regression when group pickings is disabled when
        we confirm a partial qty on a picking to create a backorder.
        """
        print("----- test_grouping test_create_backorder -----")
        so = self._get_new_sale_order(amount=10, carrier=self.carrier1)
        so.name = "SO TEST"
        so.action_confirm()
        picking = so.picking_ids
        picking.picking_type_id.group_pickings = False

        line = so.order_line.filtered(lambda line: not line.is_delivery)
        self._update_qty_in_location(
            picking.location_id,
            line.product_id,
            line.product_uom_qty,
        )
        picking.action_assign()
        line = first(picking.move_ids).move_line_ids
        line.qty_done = line.quantity_product_uom / 2
        picking._action_done()
        self.assertEqual(picking.state, "done")
        self.assertTrue(picking.backorder_ids)
        self.assertNotEqual(picking, picking.backorder_ids)
