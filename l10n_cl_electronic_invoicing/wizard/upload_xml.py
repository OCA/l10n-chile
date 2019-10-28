# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging
import base64
import xmltodict
from lxml import etree
import collections
import dicttoxml
from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

BC = """-----BEGIN CERTIFICATE-----\n"""
EC = """\n-----END CERTIFICATE-----\n"""


class UploadXMLWizard(models.TransientModel):
    _name = "sii.dte.upload_xml.wizard"
    _description = "SII XML from Provider"

    action = fields.Selection([
        ("create_po", "Crear Orden de Pedido y Factura"),
        ("create", "Crear Solamente Factura")],
        string="Action",
        default="create")
    xml_file = fields.Binary(
        string="XML File",
        filters="*.xml",
        store=True,
        help="Upload the XML File in this holder")
    filename = fields.Char(string="File Name")
    pre_process = fields.Boolean(default=True)
    dte_id = fields.Many2one("mail.message.dte", string="DTE")
    document_id = fields.Many2one("mail.message.dte.document",
                                  string="Document")
    option = fields.Selection(
        [("upload", "Upload"),
         ("accept", "Accept"),
         ("reject", "Reject")],
        string="Opción",
    )
    num_dtes = fields.Integer(string="DTES Number", readonly=True)
    type = fields.Selection(
        [("ventas", "Sales"), ("compras", "Purchase")],
        string="Operation Type",
        default="compras")

    @api.onchange("xml_file")
    def get_num_dtes(self):
        if self.xml_file:
            self.num_dtes = len(self._get_dtes())

    @api.multi
    def confirm(self, ret=False):
        created = []
        if not self.dte_id:
            dte_id = self.env["mail.message.dte"].search(
                [("name", "=", self.filename)], limit=1)
            if not dte_id:
                dte = {"name": self.filename}
                dte_id = self.env["mail.message.dte"].create(dte)
            self.dte_id = dte_id
        if self.type == "ventas":
            created = self.do_create_inv()
            xml_id = "account.action_invoice_tree2"
            target_model = "account.invoice"
        elif self.pre_process or self.action == "upload":
            created = self.do_create_pre()
            xml_id = "l10n_cl_electronic_invoicing.action_dte_process"
            target_model = "mail.message.dte"
        elif self.option == "reject":
            self.do_reject()
            return
        elif self.action == "create":
            created = self.do_create_inv()
            xml_id = "account.action_invoice_tree2"
            target_model = "account.invoice"
        if self.action == "create_po":
            self.do_create_po()
            xml_id = "purchase.purchase_order_tree"
            target_model = "purchase.order"
        if ret:
            return created
        return {
            "type": "ir.actions.act_window",
            "name": _("List of Results"),
            "view_type": "form",
            "view_mode": "tree",
            "res_model": target_model,
            "domain": str([("id", "in", created)]),
            "views": [(self.env.ref("%s" % (xml_id)).id, "tree")],
        }

    def format_rut(self, RUTEmisor=None):
        rut = RUTEmisor.replace("-", "")
        if int(rut[:-1]) < 10000000:
            rut = "0" + str(int(rut))
        rut = "CL" + rut
        return rut

    def _read_xml(self, mode="text", check=False):
        if self.document_id:
            xml = self.document_id.xml
        elif self.xml_file:
            xml = (
                base64.b64decode(self.xml_file)
                .decode("ISO-8859-1")
                .replace('<?xml version="1.0" encoding="ISO-8859-1"?>', "")
                .replace('<?xml version="1.0" encoding="ISO-8859-1" ?>', "")
            )
            if check:
                return xml
            xml = xml.replace(' xmlns="http://www.sii.cl/SiiDte"', "")
        if mode == "etree":
            parser = etree.XMLParser(remove_blank_text=True)
            return etree.fromstring(xml, parser=parser)
        if mode == "parse":
            envio = xmltodict.parse(xml)
            if "EnvioBOLETA" in envio:
                return envio["EnvioBOLETA"]
            elif "EnvioDTE" in envio:
                return envio["EnvioDTE"]
            else:
                return envio
        return xml

    def _check_digest_caratula(self):
        xml = etree.fromstring(self._read_xml(False))
        string = etree.tostring(xml[0])
        mess = etree.tostring(etree.fromstring(string), method="c14n")
        inv_obj = self.env["account.invoice"]
        base64.b64encode(inv_obj.digest(mess))
        return 0, "Envio Ok"

    def _check_digest_dte(self, dte):
        xml = self._read_xml("etree")
        envio = xml.find(
            "SetDTE"
        )
        for e in envio.findall("DTE"):
            string = etree.tostring(e.find("Documento"))  # doc
            mess = (
                etree.tostring(etree.fromstring(string), method="c14n")
                .decode("iso-8859-1")
                .replace(' xmlns:xsi='
                         '"http://www.w3.org/2001/XMLSchema-instance"', "")
                .encode("iso-8859-1")
            )  # el replace es necesario debido a que python lo agrega solo
            our = base64.b64encode(self.env["account.invoice"].digest(mess))
            their = e.find(
                "{http://www.w3.org/2000/09/xmldsig#}"
                "Signature/"
                "{http://www.w3.org/2000/09/xmldsig#}"
                "SignedInfo/"
                "{http://www.w3.org/2000/09/xmldsig#}"
                "Reference/"
                "{http://www.w3.org/2000/09/xmldsig#}"
                "DigestValue"
            ).text
            if our != their:
                _logger.warning(
                    "DTE No Recibido - Error de Firma: our = %s their=%s" %
                    (our, their)
                )
                # return 1, 'DTE No Recibido - Error de Firma'
        return 0, "DTE Recibido OK"

    def _validar_caratula(self, cara):
        try:
            self.env["account.invoice"].xml_validator(
                self._read_xml(False, check=True).encode(), "env"
            )
        except:
            return 1, "Envio Rechazado - Error de Schema"
        self.dte_id.company_id = self.env["res.company"].search(
            [("vat", "=", self.format_rut(cara["RutReceptor"]))]
        )
        if not self.dte_id.company_id:
            return 3, "Rut no corresponde a nuestra empresa"
        return 0, "Envío Ok"

    def _validar(self, doc):
        cara, glosa = self._validar_caratula(doc[0][0]["Caratula"])
        return cara, glosa

    def _validar_dte(self, doc):
        res = collections.OrderedDict()
        res["TipoDTE"] = doc["Encabezado"]["IdDoc"]["TipoDTE"]
        res["Folio"] = doc["Encabezado"]["IdDoc"]["Folio"]
        res["FchEmis"] = doc["Encabezado"]["IdDoc"]["FchEmis"]
        res["RUTEmisor"] = doc["Encabezado"]["Emisor"]["RUTEmisor"]
        res["RUTRecep"] = doc["Encabezado"]["Receptor"]["RUTRecep"]
        res["MntTotal"] = doc["Encabezado"]["Totales"]["MntTotal"]
        partner_id = self.env["res.partner"].search(
            [
                ("active", "=", True),
                ("parent_id", "=", False),
                ("vat", "=", self.format_rut(doc["Encabezado"]["Emisor"]
                                             ["RUTEmisor"])),
            ]
        )
        sii_document_class = self.env["sii.document.class"].search(
            [("sii_code", "=", str(doc["Encabezado"]["IdDoc"]["TipoDTE"]))]
        )
        res["EstadoRecepDTE"] = 0
        res["RecepDTEGlosa"] = "DTE Recibido OK"
        res["EstadoRecepDTE"], res["RecepDTEGlosa"] = \
            self._check_digest_dte(doc)
        if not sii_document_class:
            res["EstadoRecepDTE"] = 99
            res["RecepDTEGlosa"] = "Tipo de documento desconocido"
            return res
        docu = self.env["account.invoice"].search(
            [
                ("reference", "=", doc["Encabezado"]["IdDoc"]["Folio"]),
                ("partner_id", "=", partner_id.id),
                ("sii_document_class_id", "=", sii_document_class.id),
            ]
        )
        company_id = self.env["res.company"].search(
            [("vat", "=", self.format_rut(doc["Encabezado"]["Receptor"]
                                          ["RUTRecep"]))]
        )
        if not company_id and (
            not docu
            or doc["Encabezado"]["Receptor"]["RUTRecep"]
            != self.env["account.invoice"].format_vat(docu.company_id.vat)
        ):
            res["EstadoRecepDTE"] = 3
            res["RecepDTEGlosa"] = "Rut no corresponde a la empresa esperada"
            return res
        return res

    def _validar_dtes(self):
        envio = self._read_xml("parse")
        if "Documento" in envio["SetDTE"]["DTE"]:
            res = {
                "RecepcionDTE": self._validar_dte(envio["SetDTE"]["DTE"]
                                                  ["Documento"])
            }
        else:
            res = []
            for doc in envio["SetDTE"]["DTE"]:
                res.extend([{
                    "RecepcionDTE": self._validar_dte(doc["Documento"])}])
        return res

    def _caratula_respuesta(
        self, RutResponde, RutRecibe, IdRespuesta="1", NroDetalles=0
    ):
        caratula = collections.OrderedDict()
        caratula["RutResponde"] = RutResponde
        caratula["RutRecibe"] = RutRecibe
        caratula["IdRespuesta"] = IdRespuesta
        caratula["NroDetalles"] = NroDetalles
        caratula["NmbContacto"] = self.env.user.partner_id.name
        caratula["FonoContacto"] = self.env.user.partner_id.phone
        caratula["MailContacto"] = self.env.user.partner_id.email
        caratula["TmstFirmaResp"] = self.env["account.invoice"].time_stamp()
        return caratula

    def _receipt(self, IdRespuesta):
        envio = self._read_xml("parse")
        xml = self._read_xml("etree")
        resp = collections.OrderedDict()
        inv_obj = self.env["account.invoice"]
        resp["NmbEnvio"] = self.filename
        resp["FchRecep"] = inv_obj.time_stamp()
        resp["CodEnvio"] = inv_obj._acortar_str(IdRespuesta, 10)
        resp["EnvioDTEID"] = xml[0].attrib["ID"]
        resp["Digest"] = xml.find(
            "{http://www.w3.org/2000/09/xmldsig#}"
            "Signature/"
            "{http://www.w3.org/2000/09/xmldsig#}"
            "SignedInfo/"
            "{http://www.w3.org/2000/09/xmldsig#}"
            "Reference/"
            "{http://www.w3.org/2000/09/xmldsig#}"
            "DigestValue"
        ).text
        EstadoRecepEnv, RecepEnvGlosa = self._validar_caratula(
            envio["SetDTE"]["Caratula"]
        )
        if EstadoRecepEnv == 0:
            EstadoRecepEnv, RecepEnvGlosa = self._check_digest_caratula()
        resp["RutEmisor"] = envio["SetDTE"]["Caratula"]["RutEmisor"]
        resp["RutReceptor"] = envio["SetDTE"]["Caratula"]["RutReceptor"]
        resp["EstadoRecepEnv"] = EstadoRecepEnv
        resp["RecepEnvGlosa"] = RecepEnvGlosa
        NroDte = len(envio["SetDTE"]["DTE"])
        if "Documento" in envio["SetDTE"]["DTE"]:
            NroDte = 1
        resp["NroDTE"] = NroDte
        resp["item"] = self._validar_dtes()
        return resp

    def _RecepcionEnvio(self, Caratula, resultado):
        resp = """<?xml version="1.0" encoding="ISO-8859-1"?>
<RespuestaDTE version="1.0"
 xmlns="http://www.sii.cl/SiiDte"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xsi:schemaLocation="http://www.sii.cl/SiiDte RespuestaEnvioDTE_v10.xsd" >
    <Resultado ID="Odoo_resp">
        <Caratula version="1.0">
            {0}
        </Caratula>
            {1}
    </Resultado>
</RespuestaDTE>""".format(
            Caratula, resultado
        )
        return resp

    def _create_attachment(self, xml, name, res_id=False,
                           model="account.invoice"):
        data = base64.b64encode(xml.encode("ISO-8859-1"))
        filename = (name + ".xml").replace(" ", "")
        url_path = "/download/xml/resp/%s" % (res_id)
        att = self.env["ir.attachment"].search(
            [("name", "=", filename), ("res_id", "=", res_id),
             ("res_model", "=", model)],
            limit=1,
        )
        if att:
            return att
        values = dict(
            name=filename,
            datas_fname=filename,
            url=url_path,
            res_model=model,
            res_id=res_id,
            type="binary",
            datas=data,
        )
        att = self.env["ir.attachment"].create(values)
        return att

    def do_receipt_deliver(self):
        envio = self._read_xml("parse")
        if "Caratula" not in envio["SetDTE"]:
            return True
        company_id = self.env["res.company"].search(
            [("vat", "=", self.format_rut(envio["SetDTE"]["Caratula"]
                                          ["RutReceptor"]))],
            limit=1,
        )
        id_seq = self.env.ref(
            "l10n_cl_electronic_invoicing.response_sequence").id
        IdRespuesta = self.env["ir.sequence"].browse(id_seq).next_by_id()
        recep = self._receipt(IdRespuesta)
        NroDetalles = len(envio["SetDTE"]["DTE"])
        resp_dtes = (
            dicttoxml.dicttoxml(recep, root=False, attr_type=False)
            .decode()
            .replace("<item>", "\n")
            .replace("</item>", "\n")
        )
        RecepcionEnvio = """
<RecepcionEnvio>
    {0}
</RecepcionEnvio>
        """.format(
            resp_dtes
        )
        RutRecibe = envio["SetDTE"]["Caratula"]["RutEmisor"]
        caratula_recepcion_envio = self._caratula_respuesta(
            self.env["account.invoice"].format_vat(company_id.vat),
            RutRecibe,
            IdRespuesta,
            NroDetalles,
        )
        caratula = (
            dicttoxml.dicttoxml(caratula_recepcion_envio, root=False,
                                attr_type=False)
            .decode()
            .replace("<item>", "\n")
            .replace("</item>", "\n")
        )
        resp = self._RecepcionEnvio(caratula, RecepcionEnvio)
        respuesta = \
            '<?xml version="1.0" encoding="ISO-8859-1"?>\n' + \
            self.env["account.invoice"].sudo().with_context(
                {"company_id": company_id.id}).sign_full_xml(
                resp.replace('<?xml version="1.0" encoding="ISO-8859-1"?>\n',
                             ""), "Odoo_resp", "env_resp")
        if self.dte_id:
            att = self._create_attachment(
                respuesta,
                "recepcion_envio_"
                + (self.filename or self.dte_id.name)
                + "_"
                + str(IdRespuesta),
                self.dte_id.id,
                "mail.message.dte",
            )
            if att:
                values = {
                    "model_id": self.dte_id.id,
                    "email_from": company_id.dte_email,
                    "email_to": self.sudo().dte_id.mail_id.email_from,
                    "auto_delete": False,
                    "model": "mail.message.dte",
                    "body": "XML de Respuesta Envío, Estado: %s , Glosa: %s "
                    % (recep["EstadoRecepEnv"], recep["RecepEnvGlosa"]),
                    "subject": "XML de Respuesta Envío",
                    "attachment_ids": att.ids,
                }
                send_mail = self.env["mail.mail"].sudo().create(values)
                send_mail.send()
            self.dte_id.message_post(
                body=_("XML Reply, State: %s , Comment: %s ")
                % (recep["EstadoRecepEnv"], recep["RecepEnvGlosa"]),
                subject=_("XML Reply"),
                attachment_ids=att.ids,
                message_type="comment",
                subtype="mt_comment",
            )

    def _create_partner(self, data):
        rut_path = "RUTEmisor"
        if self.type == "ventas":
            rut_path = "RUTRecep"
        rut = self.format_rut(data[rut_path])
        data = {
            "name": data["RznSoc"] if self.type == "compras"
            else data["RznSocRecep"],
            "vat": rut,
            "document_type_id":
                self.env.ref("l10n_cl_electronic_invoicing.dt_RUT").id,
            "responsability_id":
                self.env.ref("l10n_cl_electronic_invoicing.res_IVARI").id,
            "document_number": data[rut_path],
            "company_type": "company",
        }
        if self.type == "compras":
            data.update({"supplier": True})
        partner_id = self.env["res.partner"].create(data)
        partner_id.onchange_document()
        return partner_id

    def _default_category(self,):
        md = self.env["ir.model.data"]
        res = False
        try:
            res = md.get_object_reference("product", "product_category_all")[1]
        except ValueError:
            res = False
        return res

    def _buscar_impuesto(
        self, name="Impuesto", amount=0, sii_code=0, sii_type=False,
            IndExe=False
    ):
        query = [
            ("sii_code", "=", sii_code),
            ("type_tax_use", "=", ("purchase" if self.type == "compras"
                                   else "sale")),
            ("activo_fijo", "=", False),
        ]
        if IndExe:
            query.append(("sii_type", "=", False))
        if amount == 0 and sii_code == 0 and not IndExe:
            query.append(("name", "=", name))
        if sii_type:
            query.extend([("sii_type", "=", sii_type)])
        imp = self.env["account.tax"].search(query)
        if not imp:
            imp = (
                self.env["account.tax"]
                .sudo()
                .create(
                    {
                        "amount": amount,
                        "name": name,
                        "sii_code": sii_code,
                        "sii_type": sii_type,
                        "type_tax_use": "purchase",
                    }
                )
            )
        return imp

    def get_product_values(self, line, price_included=False):
        IndExe = line.find("IndExe")
        amount = 0
        sii_code = 0
        sii_type = False
        if not IndExe:
            amount = 19
            sii_code = 14
            sii_type = False
        imp = self._buscar_impuesto(
            amount=amount, sii_code=sii_code, sii_type=sii_type, IndExe=IndExe
        )
        price = float(
            line.find("PrcItem").text
            if line.find("PrcItem") is not None
            else line.find("MontoItem").text
        )
        if price_included:
            price = imp.compute_all(price,
                                    self.env.user.company_id.currency_id, 1)[
                "total_excluded"
            ]
        values = {
            "sale_ok": (self.type == "ventas"),
            "name": line.find("NmbItem").text,
            "lst_price": price,
            "categ_id": self._default_category(),
            "taxes_id": [(6, 0, imp.ids)],
            "supplier_taxes_id": [(6, 0, imp.ids)],
        }
        for c in line.findall("CdgItem"):
            VlrCodigo = c.find("VlrCodigo").text
            if c.find("TpoCodigo").text == "ean13":
                values["barcode"] = VlrCodigo
            else:
                values["default_code"] = VlrCodigo
        return values

    def _create_prod(self, data, price_included=False):
        product_id = self.env["product.product"].create(
            self.get_product_values(data, price_included)
        )
        return product_id

    def _buscar_producto(self, document_id, line, price_included=False):
        _logger.warning("BUSCAR PRODUCTO")
        default_code = False
        CdgItem = line.find("CdgItem")
        NmbItem = line.find("NmbItem").text
        for c in line.findall("CdgItem"):
            _logger.warning("ENTRA A BUSCAR REFERENCIA")
            VlrCodigo = c.find("VlrCodigo").text
            query = [("default_code", "=", VlrCodigo)]
            if VlrCodigo:
                product_id = self.env["product.product"].search(query)
                if product_id:
                    _logger.warning("REFERENCIA REPETIDA")
                    return product_id.id
        if NmbItem.isspace():
            NmbItem = "Producto Genérico"
        if document_id:
            code = " " + etree.tostring(CdgItem).decode()\
                if CdgItem is not None else ""
            line_id = self.env["mail.message.dte.document.line"].search(
                [
                    "|",
                    ("new_product", "=", NmbItem + "" + code),
                    (
                        "product_description",
                        "=",
                        line.find("DescItem").text
                        if line.find("DescItem") is not None
                        else NmbItem,
                    ),
                    ("document_id", "=", document_id.id),
                ],
                limit=1,
            )
            if line_id:
                if line_id.product_id:
                    return line_id.product_id.id
            else:
                return False
        query = False
        product_id = False
        if CdgItem is not None:
            for c in line.findall("CdgItem"):
                VlrCodigo = c.find("VlrCodigo")
                TpoCodigo = c.find("TpoCodigo").text
                if TpoCodigo == "ean13":
                    query = [("barcode", "=", VlrCodigo.text)]
                elif TpoCodigo == "INT1":
                    query = [("default_code", "=", VlrCodigo.text)]
                default_code = VlrCodigo.text
        if not query:
            query = [("name", "=", NmbItem)]
        product_id = self.env["product.product"].search(query)
        query2 = [("name", "=", document_id.partner_id.id)]
        if default_code:
            query2.append(("product_code", "=", default_code))
        else:
            query2.append(("product_name", "=", NmbItem))
        product_supplier = False
        if not product_id and self.type == "compras":
            product_supplier = self.env["product.supplierinfo"].search(query2)
            product_id = product_supplier.product_id or self.env[
                "product.product"
            ].search(
                [("product_tmpl_id", "=",
                  product_supplier.product_tmpl_id.id)], limit=1
            )
            if not product_id:
                if not product_supplier and not self.pre_process:
                    product_id = self._create_prod(line, price_included)
                else:
                    code = ""
                    coma = ""
                    for c in line.findall("CdgItem"):
                        code += (
                            coma
                            + c.find("TpoCodigo").text
                            + " "
                            + c.find("VlrCodigo").text
                        )
                        coma = ", "
                    return NmbItem + "" + code
        elif self.type == "ventas" and not product_id:
            product_id = self._create_prod(line, price_included)
        if not product_supplier and document_id.partner_id and \
                self.type == "compras":
            price = float(
                line.find("PrcItem").text
                if line.find("PrcItem") is not None
                else line.find("MontoItem").text
            )
            if price_included:
                price = product_id.supplier_taxes_id.compute_all(
                    price, self.env.user.company_id.currency_id, 1
                )["total_excluded"]
            supplier_info = {
                "name": document_id.partner_id.id,
                "product_name": NmbItem,
                "product_code": default_code,
                "product_tmpl_id": product_id.product_tmpl_id.id,
                "price": price,
            }
            self.env["product.supplierinfo"].create(supplier_info)
        return product_id.id

    def _prepare_line(self, line, document_id, account_id, operation_type,
                      price_included=False):
        _logger.warning("PREPARE LINE")
        account_dummie = account_id
        data = {}
        product_id = self._buscar_producto(document_id, line, price_included)
        if isinstance(product_id, int):
            # Buscamos el modelo producto, ya que lo que tenemos es un entero
            producto = self.env["product.product"].search(
                [("product_tmpl_id", "=", product_id)], limit=1)
            # Tenemos producto, ahora buscamos la cuenta contable. En el caso
            # de que no encuentre trabajamos con account_id
            account_dummie = (producto.property_account_expense_id.id
                              if producto.property_account_expense_id.id
                              else account_id)
            if operation_type == "ventas":
                account_dummie = (
                    producto.property_account_income_id.id
                    if producto.property_account_income_id.id
                    else account_id)
            data.update({"product_id": product_id})
        elif not product_id:
            return False
        if line.find("MntExe") is not None:
            price_subtotal = float(line.find("MntExe").text)
        else:
            price_subtotal = float(line.find("MontoItem").text)
        discount = 0
        if line.find("DescuentoPct") is not None:
            discount = float(line.find("DescuentoPct").text)
        price = (
            float(line.find("PrcItem").text)
            if line.find("PrcItem") is not None
            else price_subtotal
        )
        DescItem = line.find("DescItem")
        data.update({
            "name": DescItem.text if DescItem is not None else
            line.find("NmbItem").text,
            "price_unit": price,
            "discount": discount,
            "quantity": line.find("QtyItem").text
            if line.find("QtyItem") is not None else 1,
            "account_id": account_dummie,
            "price_subtotal": price_subtotal})
        if self.pre_process and self.type == "compras":
            data.update({
                "new_product": product_id,
                "product_description": DescItem.text if DescItem is not None
                else ""})
        else:
            product_id = self.env["product.product"].browse(product_id)
            if price_included:
                price = product_id.supplier_taxes_id.compute_all(
                    price,
                    self.env.user.company_id.currency_id, 1)["total_excluded"]
                price_subtotal = product_id.supplier_taxes_id.compute_all(
                    price_subtotal,
                    self.env.user.company_id.currency_id, 1)["total_excluded"]
            data.update({
                "invoice_line_tax_ids":
                    [(6, 0, product_id.supplier_taxes_id.ids)],
                "uom_id": product_id.uom_id.id,
                "price_unit": price,
                "price_subtotal": price_subtotal})
        return [0, 0, data]

    def _create_tpo_doc(self, TpoDocRef, RazonRef=""):
        vals = {"name": RazonRef + " " + str(TpoDocRef)}
        if str(TpoDocRef).isdigit():
            vals.update({"sii_code": TpoDocRef})
        else:
            vals.update(
                {"doc_code_prefix": TpoDocRef,
                 "sii_code": 801,
                 "use_prefix": True}
            )
        return self.env["sii.document.class"].create(vals)

    def _prepare_ref(self, ref):
        query = []
        TpoDocRef = ref.find("TpoDocRef").text
        RazonRef = ref.find("RazonRef").text
        if str(TpoDocRef).isdigit():
            query.append(("sii_code", "=", TpoDocRef))
            query.append(("use_prefix", "=", False))
        else:
            query.append(("doc_code_prefix", "=", TpoDocRef))
        tpo = self.env["sii.document.class"].search(query, limit=1)
        if not tpo:
            tpo = self._create_tpo_doc(TpoDocRef, RazonRef)
        return [
            0,
            0,
            {
                "origen": ref.find("FolioRef").text,
                "sii_referencia_TpoDocRef": tpo.id,
                "sii_referencia_CodRef": ref.find("CodRef").text
                if ref.find("CodRef") is not None
                else None,
                "motivo": RazonRef if RazonRef is not None else None,
                "fecha_documento": ref.find("FchRef").text
                if ref.find("FchRef") is not None
                else None,
            },
        ]

    def process_dr(self, dr):
        data = {"type": dr.find("TpoMov").text}
        disc_type = "percent"
        if dr.find("TpoValor").text == "$":
            disc_type = "amount"
        data["gdr_type"] = disc_type
        data["valor"] = dr.find("ValorDR").text
        data["gdr_dtail"] = (
            dr.find("GlosaDR").text
            if dr.find("GlosaDR") is not None
            else "Descuento globla"
        )
        return data

    def _prepare_invoice(self, documento, company_id,
                         journal_document_class_id):
        operation_type = "Emisor"
        rut_path = "RUTEmisor"
        if self.type == "ventas":
            operation_type = "Receptor"
            rut_path = "RUTRecep"
        Encabezado = documento.find("Encabezado")
        IdDoc = Encabezado.find("IdDoc")
        Emisor = Encabezado.find(operation_type)
        RUT = Emisor.find(rut_path).text
        string = etree.tostring(documento)
        dte = xmltodict.parse(string)["Documento"]
        invoice = {"account_id": False}
        partner_id = self.env["res.partner"].search([
            ("active", "=", True),
            ("parent_id", "=", False),
            ("vat", "=", self.format_rut(RUT))])
        _logger.warning("Creando el Partner")
        if not partner_id:
            partner_id = self._create_partner(dte["Encabezado"][operation_type])
        elif not partner_id.supplier and self.type == "compras":
            partner_id.supplier = True
        invoice["type"] = "in_invoice"
        if self.type == "ventas":
            invoice["type"] = "out_invoice"
        if dte["Encabezado"]["IdDoc"]["TipoDTE"] in ["54", "61"]:
            invoice["type"] = "in_refund"
            if self.type == "ventas":
                invoice["type"] = "out_refund"
        if partner_id:
            account_id = (
                partner_id.property_account_payable_id.id
                or journal_document_class_id.journal_id.
                default_debit_account_id.id)
            if invoice["type"] in ("out_invoice", "in_refund"):
                account_id = (
                    partner_id.property_account_receivable_id.id
                    or journal_document_class_id.journal_id.
                    default_credit_account_id.id)
            invoice.update({"account_id": account_id,
                            "partner_id": partner_id.id})
            partner_id = partner_id.id
        try:
            name = self.filename.decode("ISO-8859-1").encode("UTF-8")
        except UnicodeEncodeError:
            name = self.filename.encode("UTF-8")
        ted_string = etree.tostring(
            documento.find("TED"), method="c14n", pretty_print=False)
        FchEmis = IdDoc.find("FchEmis").text
        xml_envio = self.env["sii.xml.envio"].create({
            "name": "ENVIO_%s" % name.decode(),
            "xml_envio": string.decode(),
            "state": "Aceptado"})
        invoice.update({
            "origin": "XML Envío: " + name.decode(),
            "date_invoice": FchEmis,
            "partner_id": partner_id,
            "company_id": company_id.id,
            "journal_id": journal_document_class_id.journal_id.id,
            "sii_xml_request": xml_envio.id,
            "sii_barcode": ted_string.decode()})
        DscRcgGlobal = documento.findall("DscRcgGlobal")
        if DscRcgGlobal:
            drs = [(5,)]
            for dr in DscRcgGlobal:
                drs.append((0, 0, self.process_dr(dr)))
            invoice.update({"global_descuentos_recargos": drs})
        Folio = IdDoc.find("Folio").text
        if partner_id and not self.pre_process and self.type == "compras":
            invoice.update({
                "reference": Folio,
                "journal_document_class_id": journal_document_class_id.id})
        elif self.type == "ventas":
            invoice.update({
                "sii_document_number": Folio,
                "journal_document_class_id": journal_document_class_id.id,
                "state": "open"})
        else:
            invoice.update({
                "number": Folio,
                "date": FchEmis,
                "new_partner": RUT + " " + Emisor.find("RznSoc").text,
                "sii_document_class_id":
                    journal_document_class_id.sii_document_class_id.id,
                "amount": dte["Encabezado"]["Totales"]["MntTotal"]})
        return invoice

    def _get_journal(self, sii_code, company_id):
        operation_type = "purchase"
        if self.type == "ventas":
            operation_type = "sale"
        return self.env["account.journal.sii.document.class"].search([
            ("sii_document_class_id.sii_code", "=", sii_code),
            ("journal_id.type", "=", operation_type),
            ("journal_id.company_id", "=", company_id.id)], limit=1)

    def _get_data(self, documento, company_id):
        string = etree.tostring(documento)
        dte = xmltodict.parse(string)["Documento"]
        Encabezado = documento.find("Encabezado")
        IdDoc = Encabezado.find("IdDoc")
        price_included = Encabezado.find("MntBruto")
        journal_document_class_id = self._get_journal(
            IdDoc.find("TipoDTE").text, company_id
        )
        if not journal_document_class_id:
            sii_document_class = self.env["sii.document.class"].search(
                [("sii_code", "=", IdDoc.find("TipoDTE").text)]
            )
            raise UserError(_(
                "No existe Diario para el tipo de documento %s, por favor"
                " añada uno primero, o ignore el documento"
                % sii_document_class.name.encode("UTF-8")))
        data = self._prepare_invoice(documento, company_id,
                                     journal_document_class_id)
        lines = [(5,)]
        document_id = self._dte_exist(documento)
        # Lineas de Facturas con Cuentas de Ingreso y Gastos por Defecto
        categoria = self.env["product.category"].search(
            [("name", "=", "All")], limit=1)
        if not categoria:
            categoria = self.env["product.category"].search([], limit=1)
        # Aqui queremos trabajar con la cuenta del producto seleccionado
        # Por ahora categoria generica y sino producto X
        if self.type == "ventas":
            if categoria.property_account_income_categ_id.id:
                account_id = categoria.property_account_income_categ_id.id
            else:
                account_id = self.env.ref(
                    "l10n_cl_electronic_invoicing.producto_afecto"
                ).categ_id.property_account_income_categ_id.id
        else:
            if categoria.property_account_expense_categ_id.id:
                account_id = categoria.property_account_expense_categ_id.id
            else:
                account_id = self.env.ref(
                    "l10n_cl_electronic_invoicing.producto_afecto"
                ).categ_id.property_account_expense_categ_id.id
        for line in documento.findall("Detalle"):
            new_line = self._prepare_line(
                line,
                document_id=document_id,
                account_id=account_id,
                type=data["type"],
                price_included=price_included,
            )
            if new_line:
                lines.append(new_line)
        product_id = (
            self.env["product.product"]
            .search(
                [("product_tmpl_id", "=", self.env.ref(
                    "l10n_cl_electronic_invoicing.product_imp").id)]
            )
            .id
        )
        if "ImptoReten" in dte["Encabezado"]["Totales"]:
            Totales = dte["Encabezado"]["Totales"]
            if "TipoImp" in Totales["ImptoReten"]:
                TipoImp = (
                    str([Totales["ImptoReten"]["TipoImp"]])
                    .replace("['", "")
                    .replace("']", "")
                )
                MontoImp = (
                    str([Totales["ImptoReten"]["MontoImp"]])
                    .replace("['", "")
                    .replace("']", "")
                )

                imp = self._buscar_impuesto(
                    name="OtrosImps_" + str(TipoImp), sii_code=TipoImp
                )
                price = float(MontoImp)
                price_subtotal = float(MontoImp)
                if price_included:
                    price = imp.compute_all(
                        price, self.env.user.company_id.currency_id, 1
                    )["total_excluded"]
                    price_subtotal = imp.compute_all(
                        price_subtotal, self.env.user.company_id.currency_id, 1
                    )["total_excluded"]
                lines.append(
                    [
                        0,
                        0,
                        {
                            "invoice_line_tax_ids": ((6, 0, imp.ids)),
                            "product_id": product_id,
                            "name": "Impuesto %s" % str(TipoImp),
                            "price_unit": price,
                            "quantity": 1,
                            "price_subtotal": price_subtotal,
                            "account_id":
                                journal_document_class_id.journal_id.
                                    default_debit_account_id.id,
                        },
                    ]
                )
        reference_ids = documento.findall("Referencia")
        if not self.pre_process and reference_ids:
            refs = [(5,)]
            try:
                for ref in reference_ids:
                    refs.append(self._prepare_ref(ref))
                data["reference_ids"] = refs
            except:
                _logger.warning("No puede cargar reference_ids")
        data["invoice_line_ids"] = lines
        mnt_neto = (
            int(dte["Encabezado"]["Totales"]["MntNeto"])
            if "MntNeto" in dte["Encabezado"]["Totales"]
            else 0
        )
        mnt_neto += (
            int(dte["Encabezado"]["Totales"]["MntExe"])
            if "MntExe" in dte["Encabezado"]["Totales"]
            else 0
        )
        data["amount_untaxed"] = mnt_neto
        data["amount_total"] = dte["Encabezado"]["Totales"]["MntTotal"]
        _logger.warning("10")
        if document_id:
            purchase_to_done = False
            if document_id.purchase_to_done:
                purchase_to_done = document_id.purchase_to_done.ids()
            if purchase_to_done:
                data["purchase_to_done"] = purchase_to_done
        return data

    def _inv_exist(self, documento):
        encabezado = documento.find("Encabezado")
        Emisor = encabezado.find("Emisor")
        IdDoc = encabezado.find("IdDoc")
        operation_type = ["in_invoice", "in_refund"]
        if self.type == "ventas":
            operation_type = ["out_invoice", "out_refund"]
        return self.env["account.invoice"].search([
            ("reference", "=", IdDoc.find("Folio").text),
            ("type", "in", operation_type),
            ("sii_document_class_id.sii_code", "=",
             IdDoc.find("TipoDTE").text),
            ("partner_id.vat", "=",
             self.format_rut(Emisor.find("RUTEmisor").text))])

    def _create_inv(self, documento, company_id):
        inv = self._inv_exist(documento)
        if inv:
            return inv
        _logger.warning("Encabezado/Totales")
        Totales = documento.find("Encabezado/Totales")
        _logger.warning("get_data")
        data = self._get_data(documento, company_id)
        _logger.warning("CREATE ...")
        inv = self.env["account.invoice"].create(data)
        _logger.warning(_("Entrando a MntTotal "))
        monto_xml = float(Totales.find("MntTotal").text)
        if inv.amount_total == monto_xml:
            return inv
        inv.amount_total = monto_xml
        for t in inv.tax_line_ids:
            if Totales.find("TasaIVA") is not None and \
                    t.tax_id.amount == float(
                Totales.find("TasaIVA").text
            ):
                t.amount = float(Totales.find("IVA").text)
                t.base = float(Totales.find("MntNeto").text)
            else:
                t.base = float(Totales.find("MntExe").text)
        return inv

    def _dte_exist(self, documento):
        encabezado = documento.find("Encabezado")
        Emisor = encabezado.find("Emisor")
        IdDoc = encabezado.find("IdDoc")
        return self.env["mail.message.dte.document"].search(
            [
                ("number", "=", IdDoc.find("Folio").text),
                ("sii_document_class_id.sii_code", "=",
                 IdDoc.find("TipoDTE").text),
                "|",
                ("partner_id.vat", "=",
                 self.format_rut(Emisor.find("RUTEmisor").text)),
                (
                    "new_partner",
                    "=",
                    Emisor.find("RUTEmisor").text + " " +
                    Emisor.find("RznSoc").text,
                ),
            ],
            limit=1,
        )

    def _create_pre(self, documento, company_id):
        dte = self._dte_exist(documento)
        if dte:
            _logger.warning(_("El documento ya se encuentra registrado"))
            return dte
        data = self._get_data(documento, company_id)
        data.update({"dte_id": self.dte_id.id})
        return self.env["mail.message.dte.document"].create(data)

    def _get_dtes(self):
        xml = self._read_xml("etree")
        if xml.tag == "SetDTE":
            return xml.findall("DTE")
        envio = xml.find("SetDTE")
        if envio is None:
            if xml.tag == "DTE":
                return [xml]
            return []
        return envio.findall("DTE")

    def do_create_pre(self):
        created = []
        self.do_receipt_deliver()
        dtes = self._get_dtes()
        for dte in dtes:
            try:
                documento = dte.find("Documento")
                company_id = self.env["res.company"].search(
                    [
                        (
                            "vat",
                            "=",
                            self.format_rut(
                                documento.find(
                                    "Encabezado/Receptor/RUTRecep").text
                            ),
                        )
                    ],
                    limit=1,
                )
                if not company_id:
                    _logger.warning(
                        "No existe compañia para %s"
                        % documento.find("Encabezado/Receptor/RUTRecep").text
                    )
                    continue
                pre = self._create_pre(documento, company_id)
                if pre:
                    inv = self._inv_exist(documento)
                    pre.write({"xml": etree.tostring(dte),
                               "invoice_id": inv.id})
                    created.append(pre.id)
            except Exception as e:
                _logger.warning("Error en 1 factura con error:  %s" % str(e))
        return created

    def do_create_inv(self):
        created = []
        dtes = self._get_dtes()
        for dte in dtes:
            try:
                company_id = self.document_id.company_id
                documento = dte.find("Documento")
                path_rut = "Encabezado/Receptor/RUTRecep"
                if self.type == "ventas":
                    path_rut = "Encabezado/Emisor/RUTEmisor"
                company_id = self.env["res.company"].search(
                    [("vat", "=",
                      self.format_rut(documento.find(path_rut).text))],
                    limit=1,
                )
                _logger.warning("EMPRESA EMISORA %s" % company_id.name)
                inv = self._create_inv(documento, company_id)
                if self.document_id:
                    self.document_id.invoice_id = inv.id
                if inv:
                    created.append(inv.id)
                if not inv:
                    raise UserError(_(
                        "The XML file does not contain documents for any "
                        "company in Odoo, or it has already been processed."))
            except Exception as e:
                _logger.warning("Error en crear 1 factura con error:  %s"
                                % str(e))
        if created and self.option not in [False, "upload"] and\
                self.type == "compras":
            wiz_accept = self.env["sii.dte.validar.wizard"].create(
                {
                    "invoice_ids": [(6, 0, created)],
                    "action": "validate",
                    "option": self.option,
                }
            )
            wiz_accept.confirm()
        return created

    def prepare_purchase_line(self, line, date_planned):
        product = self.env["product.product"].search(
            [("name", "=", line["NmbItem"])], limit=1
        )
        if not product:
            product = self._create_prod(line)
        values = {
            "name":
                line["DescItem"] if "DescItem" in line else line["NmbItem"],
            "product_id": product.id,
            "product_uom": product.uom_id.id,
            "taxes_id": [(6, 0, product.supplier_taxes_id.ids)],
            "price_unit": float(
                line["PrcItem"] if "PrcItem" in line else line["MontoItem"]),
            "product_qty": line["QtyItem"],
            "date_planned": date_planned,
        }
        return values

    def _create_po(self, dte):
        purchase_model = self.env["purchase.order"]
        partner_id = self.env["res.partner"].search(
            [
                ("active", "=", True),
                ("parent_id", "=", False),
                ("vat", "=", self.format_rut(dte["Encabezado"]["Emisor"]
                                             ["RUTEmisor"])),
            ]
        )
        if not partner_id:
            partner_id = self._create_partner(dte["Encabezado"]["Emisor"])
        elif not partner_id.supplier:
            partner_id.supplier = True
        company_id = self.env["res.company"].search(
            [("vat", "=", self.format_rut(dte["Encabezado"]["Receptor"]
                                          ["RUTRecep"]))]
        )
        data = {
            "partner_ref": dte["Encabezado"]["IdDoc"]["Folio"],
            "date_order": dte["Encabezado"]["IdDoc"]["FchEmis"],
            "partner_id": partner_id.id,
            "company_id": company_id.id,
        }
        # antes de crear la OC, verificar que no exista otro documento con los
        # mismos datos
        other_orders = purchase_model.search(
            [
                ("partner_id", "=", data["partner_id"]),
                ("partner_ref", "=", data["partner_ref"]),
                ("company_id", "=", data["company_id"]),
            ]
        )
        if other_orders:
            raise UserError(_(
                "There is already a purchase order with the reference: %s for "
                "this vendor: %s.\n"
                "You cannot create a new one. Please check."
                % (data["partner_ref"], partner_id.name)))
        lines = [(5,)]
        vals_line = {}
        detalles = dte["Detalle"]
        # cuando es un solo producto, no viene una lista sino un diccionario
        # asi que tratarlo como una lista de un solo elemento
        # para evitar error en la esructura que siempre espera una lista
        if isinstance(dte["Detalle"], dict):
            detalles = [dte["Detalle"]]
        for line in detalles:
            vals_line = self.prepare_purchase_line(
                line, dte["Encabezado"]["IdDoc"]["FchEmis"])
            if vals_line:
                lines.append([0, 0, vals_line])

        data["order_line"] = lines
        po = purchase_model.create(data)
        po.button_confirm()
        return po

    def do_create_po(self):
        # self.validate()
        dtes = self._get_dtes()
        for dte in dtes:
            if dte["Documento"]["Encabezado"]["IdDoc"]["TipoDTE"] in \
                    ["34", "33"]:
                self._create_po(dte["Documento"])
            elif dte["Documento"]["Encabezado"]["IdDoc"]["TipoDTE"] in \
                    ["56", "61"]:  # es una nota
                self._create_inv(dte["Documento"])
