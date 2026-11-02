# Copyright 2026 Fernando San Martin Woerner <fsanmartin@iternova.cl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from odoo import _, fields
from odoo.exceptions import ValidationError


class InvoiceSnapshotService:
    """Build immutable fiscal input from a posted Chilean invoice."""

    # This adapter serializes DTE_v10 invoices. Boletas (39/41) have a separate
    # SII format and lifecycle and must not enter this pipeline.
    SUPPORTED_DOCUMENT_CODES = frozenset({"33", "34"})

    def validate_invoice_source(self, move, document_code):
        """Validate source and fiscal master data before reserving a folio."""
        move.ensure_one()
        document_code = str(document_code)
        self._validate_invoice(move, document_code)

    def capture_invoice(self, move, caf_authorization, folio_number, document_code):
        """Return a serializable snapshot for the selected document type."""
        move.ensure_one()
        caf_authorization.ensure_one()
        document_code = str(document_code)
        company, activity_code = self._validate_invoice(move, document_code)
        self._validate_caf(caf_authorization, company, folio_number, document_code)
        folio_number = int(folio_number)
        invoice_lines = move.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
        )
        line_snapshots, taxable_net, exempt_net = self._snapshot_lines(invoice_lines)
        net_total = self._integer_amount(move.amount_untaxed, "invoice untaxed amount")
        vat_total = self._integer_amount(move.amount_tax, "invoice tax amount")
        total = self._integer_amount(move.amount_total, "invoice total")
        if taxable_net + exempt_net != net_total:
            raise ValidationError(
                _("Invoice lines do not reconcile to the posted untaxed amount.")
            )
        if document_code in {"34", "41"} and taxable_net:
            raise ValidationError(
                _("DTE type %(code)s must contain only exempt lines.")
                % {"code": document_code}
            )
        if taxable_net and not vat_total:
            raise ValidationError(_("The taxable invoice has no posted VAT amount."))

        current_timestamp = self._chile_timestamp()
        return {
            "company_id": company.id,
            "document_code": document_code,
            "folio": folio_number,
            "issue_date": fields.Date.to_date(move.invoice_date).isoformat(),
            "document_timestamp": current_timestamp,
            "ted_timestamp": current_timestamp,
            "issuer": self._partner_snapshot(
                company.partner_id,
                activity=company.l10n_cl_activity_description,
                activity_code=activity_code,
            ),
            "receiver": self._partner_snapshot(move.partner_id.commercial_partner_id),
            "totals": {
                "net": str(int(taxable_net)) if taxable_net else None,
                "exempt": str(int(exempt_net)) if exempt_net else None,
                "vat_rate": "19" if taxable_net else None,
                "vat": str(int(vat_total)) if taxable_net else None,
                "total": str(int(total)),
            },
            "lines": line_snapshots,
        }

    def _validate_invoice(self, move, document_code):
        if document_code not in self.SUPPORTED_DOCUMENT_CODES:
            raise ValidationError(
                _("DTE type %(code)s is not supported by this issuance flow.")
                % {"code": document_code}
            )
        if move.state != "posted" or move.move_type != "out_invoice":
            raise ValidationError(
                _("A DTE can only be created from a posted customer invoice.")
            )
        if move.l10n_latam_document_type_id.code != document_code:
            raise ValidationError(
                _("The selected DTE type does not match the accounting document.")
            )
        company = move.company_id
        if company.partner_id.country_id.code != "CL":
            raise ValidationError(_("The issuing company must be registered in Chile."))
        if move.currency_id.name != "CLP":
            raise ValidationError(_("This issuance flow supports CLP invoices only."))
        if not move.invoice_date:
            raise ValidationError(_("The invoice must have an issue date."))
        errors = self._fiscal_master_data_errors(move, document_code)
        if errors:
            raise ValidationError(
                _("Complete the required fiscal data before issuing the DTE:\n%s")
                % "\n".join(f"• {error}" for error in errors)
            )
        activity_code = company.dte_sii_activity_code.strip()
        return company, activity_code

    def _validate_caf(self, caf_authorization, company, folio_number, document_code):
        if caf_authorization.company_id != company:
            raise ValidationError(_("The CAF and invoice companies do not match."))
        if caf_authorization.document_code != document_code:
            raise ValidationError(
                _("The CAF does not match the selected DTE document type.")
            )
        caf_model = company.env["l10n_cl.caf.authorization"]
        company_vat = caf_model._normalize_vat(company.partner_id.vat)
        caf_vat = caf_model._normalize_vat(caf_authorization.issuer_vat)
        if not caf_model._is_valid_vat(company_vat) or company_vat != caf_vat:
            raise ValidationError(
                _("The company RUT no longer matches the selected CAF issuer.")
            )
        folio_number = int(folio_number)
        if (
            not caf_authorization.folio_start
            <= folio_number
            <= caf_authorization.folio_end
        ):
            raise ValidationError(_("The folio is outside the CAF range."))

    def _fiscal_master_data_errors(self, move, document_code):
        caf_model = move.env["l10n_cl.caf.authorization"]
        errors = []
        issuer = move.company_id.partner_id
        issuer_vat = caf_model._normalize_vat(issuer.vat)
        if not caf_model._is_valid_vat(issuer_vat):
            errors.append(_("Company: enter a valid Chilean RUT."))
        if not (issuer.name or "").strip():
            errors.append(_("Company: enter the legal name."))
        if not (issuer.l10n_cl_activity_description or "").strip():
            errors.append(_("Company: enter the SII economic activity."))
        activity_code = (move.company_id.dte_sii_activity_code or "").strip()
        if not activity_code.isdigit() or int(activity_code or "0") <= 0:
            errors.append(_("Company: enter a valid SII activity code."))
        if not " ".join(
            part.strip() for part in (issuer.street, issuer.street2) if part
        ):
            errors.append(_("Company: enter the DTE origin address."))
        if not (issuer.city or "").strip():
            errors.append(_("Company: enter the DTE origin commune."))

        receiver = move.partner_id.commercial_partner_id
        receiver_vat = caf_model._normalize_vat(receiver.vat)
        if not caf_model._is_valid_vat(receiver_vat):
            errors.append(_("Customer: enter a valid Chilean RUT."))
        if not (receiver.name or "").strip():
            errors.append(_("Customer: enter a name for the DTE recipient."))
        if not " ".join(
            part.strip() for part in (receiver.street, receiver.street2) if part
        ):
            errors.append(_("Customer: enter the DTE delivery/service address."))
        if not (receiver.city or "").strip():
            errors.append(_("Customer: enter the DTE recipient commune."))
        if document_code in {"33", "34"} and receiver_vat == "666666666":
            errors.append(
                _(
                    "DTE types 33 and 34 require an identified recipient; for an "
                    "anonymous final consumer, select type 39; boleta issuance is "
                    "not available in this flow yet."
                )
            )
        return errors

    def _snapshot_lines(self, invoice_lines):
        if not invoice_lines:
            raise ValidationError(_("The invoice needs at least one product line."))
        if len(invoice_lines) > 60:
            raise ValidationError(_("A DTE supports at most 60 detail lines."))

        line_snapshots = []
        taxable_net = Decimal("0")
        exempt_net = Decimal("0")
        for line in invoice_lines:
            taxable = self._is_taxable_19_percent(line.tax_ids)
            subtotal = self._integer_amount(
                line.price_subtotal, "invoice line subtotal"
            )
            if taxable:
                taxable_net += subtotal
            else:
                exempt_net += subtotal
            item_name = (line.product_id.name or line.name or "").strip()
            detail_description = (line.name or item_name).strip()
            if not item_name or len(item_name) > 80:
                raise ValidationError(
                    _(
                        "Each invoice product name must contain between 1 and 80 "
                        "characters."
                    )
                )
            if len(detail_description) > 1000:
                raise ValidationError(
                    _("Invoice line descriptions cannot exceed 1000 characters.")
                )
            line_snapshots.append(
                {
                    "name": item_name,
                    "description": detail_description,
                    "quantity": self._decimal_text(line.quantity),
                    "uom": (line.product_uom_id.name or "")[:4],
                    "unit_price": self._decimal_text(line.price_unit),
                    "discount_percent": self._decimal_text(line.discount)
                    if line.discount
                    else None,
                    "subtotal": str(int(subtotal)),
                    "exempt": not taxable,
                }
            )

        return line_snapshots, taxable_net, exempt_net

    def _is_taxable_19_percent(self, taxes):
        percentages = set()
        for tax in taxes:
            if tax.amount == 0:
                continue
            if tax.amount_type != "percent" or abs(tax.amount) != 19:
                raise ValidationError(
                    _("This issuance flow supports only 19% VAT and exempt lines.")
                )
            percentages.add(abs(tax.amount))
        if len(percentages) > 1:
            raise ValidationError(
                _("An invoice line cannot mix VAT rates in this flow.")
            )
        return bool(percentages)

    def _partner_snapshot(self, partner, activity=None, activity_code=None):
        street = " ".join(
            part.strip() for part in (partner.street, partner.street2) if part
        )
        return {
            "vat": (partner.vat or "").strip(),
            "name": (partner.name or "").strip(),
            "activity": (
                activity or getattr(partner, "l10n_cl_activity_description", "") or ""
            ).strip(),
            "activity_code": activity_code,
            "address": street,
            "commune": (partner.city or "").strip(),
            "city": (partner.state_id.name or "").strip(),
        }

    def _integer_amount(self, value, label):
        amount = self._decimal(value)
        if amount != amount.to_integral_value():
            raise ValidationError(
                _("CLP %(label)s must be an integer amount.") % {"label": label}
            )
        return amount

    def _decimal_text(self, value):
        return format(self._decimal(value).normalize(), "f")

    def _decimal(self, value):
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError(
                _("Invoice monetary values must be numeric.")
            ) from error
        if not amount.is_finite():
            raise ValidationError(_("Invoice monetary values must be finite."))
        return amount

    def _chile_timestamp(self):
        return datetime.now(ZoneInfo("America/Santiago")).strftime("%Y-%m-%dT%H:%M:%S")
