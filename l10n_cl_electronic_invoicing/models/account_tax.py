# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class SiiTax(models.Model):
    _inherit = "account.tax"

    @api.multi
    def compute_all(
        self,
        price_unit,
        currency=None,
        quantity=1.0,
        product=None,
        partner=None,
        discount=None,
    ):
        """ Returns all information required to apply taxes (in self + their
         children in case of a tax goup).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as
                 sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]
        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'taxes': [{               # One dict for each tax in self and
                                      # their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }]
        } """
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        prec = currency.decimal_places

        # In some cases, it is necessary to force/prevent the rounding of the
        # tax and the total amounts. For example, in SO/PO line, we don't want
        # to round the price unit at the precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = (
            False
            if company_id.tax_calculation_rounding_method == "round_globally"
            else True
        )
        round_total = True
        if "round" in self.env.context:
            round_tax = bool(self.env.context["round"])
            round_total = bool(self.env.context["round"])

        if not round_tax:
            prec += 5

        base_values = self.env.context.get("base_values")
        if not base_values:
            base = round(price_unit * quantity, prec + 2)
            base = round(base, prec)
            tot_discount = currency.round(base * ((discount or 0.0) / 100))
            base -= tot_discount
            total_excluded = base
            total_included = base
        else:
            total_excluded, total_included, base = base_values

        # Sorting key is mandatory in this case. When no key is provided,
        # sorted() will perform a search. However, the search method is
        # overridden in account.tax in order to add a domain depending on the
        # context. This domain might filter out some taxes from self, e.g. in
        # the case of group taxes.
        for tax in self.sorted(key=lambda r: r.sequence):
            # Allow forcing price_include/include_base_amount through the
            # context for the reconciliation widget.
            # See task 24014.
            price_include = self._context.get("force_price_include",
                                              tax.price_include)

            if tax.amount_type == "group":
                children = tax.children_tax_ids.with_context(
                    base_values=(total_excluded, total_included, base)
                )
                ret = children.compute_all(
                    price_unit, currency, quantity, product, partner
                )
                total_excluded = ret["total_excluded"]
                base = ret["base"] if tax.include_base_amount else base
                total_included = ret["total_included"]
                tax_amount_retention = ret["retention"]
                tax_amount = \
                    total_included - total_excluded + tax_amount_retention
                taxes += ret["taxes"]
                continue

            tax_amount = tax._compute_amount(
                base, price_unit, quantity, product, partner
            )
            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = currency.round(tax_amount)
            tax_amount_retention = 0
            if tax.sii_type in ["R"]:
                tax_amount_retention = tax._compute_amount_ret(
                    base, price_unit, quantity, product, partner
                )
                if not round_tax:
                    tax_amount_retention = round(tax_amount_retention, prec)
            if price_include:
                total_excluded -= tax_amount - tax_amount_retention
                total_included -= tax_amount_retention
                base -= tax_amount - tax_amount_retention
            else:
                total_included += tax_amount - tax_amount_retention

            # Keep base amount used for the current tax
            tax_base = base

            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                "id": tax.id,
                "name": tax.with_context(
                    **{"lang": partner.lang} if partner else {}).name,
                "amount": tax_amount,
                "retention": tax_amount_retention,
                "base": tax_base,
                "sequence": tax.sequence,
                "account_id": tax.account_id.id,
                "refund_account_id": tax.refund_account_id.id,
                "analytic": tax.analytic,
                "price_include": tax.price_include,
                "tax_exigibility": tax.tax_exigibility}
            )

        return {
            "taxes": sorted(taxes, key=lambda k: k["sequence"]),
            "total_excluded":
                round_total and currency.round(total_excluded)
                or total_excluded,
            "total_included":
                round_total and currency.round(total_included)
                or total_included,
            "base": base,
        }

    def _compute_amount_ret(
        self, base_amount, price_unit, quantity=1.0, product=None, partner=None
    ):
        if self.amount_type == "percent" and self.price_include:
            neto = base_amount / (1 + self.retencion / 100)
            tax = base_amount - neto
            return tax
        if (self.amount_type == "percent" and not self.price_include) or (
            self.amount_type == "division" and self.price_include
        ):
            return base_amount * self.retencion / 100
