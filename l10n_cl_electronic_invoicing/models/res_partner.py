# Copyright (C) 2019 Konos
# Copyright (C) 2019 Blanco Martín & Asociados
# Copyright (C) 2019 CubicERP
# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import re
import logging
import requests
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _get_default_tp_type(self):
        try:
            return self.env.ref("l10n_cl_electronic_invoicing.res_IVARI")
        except:
            return self.env["sii.responsability"]

    def _get_default_doc_type(self):
        try:
            return self.env.ref("l10n_cl_electronic_invoicing.dt_RUT")
        except:
            return self.env["sii.document.type"]

    @api.model
    def _get_default_country(self):
        return (
            self.env.user.company_id.country_id.id
            or self.env.user.partner_id.country_id.id
        )

    responsability_id = fields.Many2one(
        "sii.responsability",
        string="Responsability",
        default=lambda self: self._get_default_tp_type(),
    )
    document_type_id = fields.Many2one(
        "sii.document.type",
        string="Document type",
        default=lambda self: self._get_default_doc_type(),
    )
    document_number = fields.Char(string="Document number", size=64)
    start_date = fields.Date(string="Start-up Date")
    tp_sii_code = fields.Char(
        "Tax Payer SII Code", compute="_compute_tp_sii_code", readonly=True
    )
    activity_description = fields.Many2one(
        "sii.activity.description", string="Glosa Giro", ondelete="restrict"
    )
    dte_email = fields.Char(string="DTE Email")

    @api.multi
    @api.onchange("responsability_id")
    def _compute_tp_sii_code(self):
        for record in self:
            record.tp_sii_code = str(record.responsability_id.tp_sii_code)

    def find_between_r(self, s, first, last):
        try:
            start = s.rindex(first) + len(first)
            end = s.rindex(last, start)
            return s[start:end]
        except ValueError:
            return ""

    @api.onchange("document_number", "document_type_id")
    def onchange_document(self):
        mod_obj = self.env["ir.model.data"]
        if self.document_number and (
            ("sii.document.type", self.document_type_id.id)
            == mod_obj.get_object_reference("l10n_cl_electronic_invoicing",
                                            "dt_RUT")
            or ("sii.document.type", self.document_type_id.id)
            == mod_obj.get_object_reference("l10n_cl_electronic_invoicing",
                                            "dt_RUN")
        ):
            document_number = (
                (re.sub("[^1234567890Kk]", "", str(self.document_number)))
                .zfill(9)
                .upper()
            )
            if not self.check_vat_cl(document_number):
                return {
                    "warning": {"title": _("Rut Erróneo"),
                                "message": _("Rut Erróneo")}
                }

            vat = "CL%s" % document_number
            exist = self.env["res.partner"].search(
                [
                    ("vat", "=", vat),
                    ("vat", "!=", "CL555555555"),
                    ("commercial_partner_id", "!=",
                     self.commercial_partner_id.id),
                ],
                limit=1,
            )
            if exist:
                # En este caso, el numero de documento esta siendo utilizado
                # por otro contacto.
                # Entonces se debe quitar el valor de document_number y vat
                # para que no esten duplicados. Y se envia un mensaje al
                # usuario para que sepa lo que esta pasando pero cuando se
                # utiliza el boton de actualizar RUT, el mensaje al usuario no
                # se muestra, por lo tanto dejo un mensaje en el log de Odoo
                _logger.warning(
                    "El contacto %s está utilizando este numero de documento"
                    % (exist.name)
                )
                self.vat = ""
                self.document_number = ""
                return {
                    "warning": {
                        "title": "Informacion para el Usuario",
                        "message": _(
                            "El contacto %s está utilizando este numero de "
                            "documento"
                        )
                        % exist.name,
                    }
                }
            self.vat = vat
            self.document_number = "%s.%s.%s-%s" % (
                document_number[0:2],
                document_number[2:5],
                document_number[5:8],
                document_number[-1],
            )
            otro = "%s%s%s-%s" % (
                document_number[0:2],
                document_number[2:5],
                document_number[5:8],
                document_number[-1],
            )

            try:
                if otro[:1] == "0":
                    otro = otro[1:]
                url = "http://api.konos.cl:8000/sii/index.php?id=%s" % otro
                response = requests.get(url, params="nombre")
            except Exception:
                response = False

            if response and response.status_code != 200:
                _logger.warning("error %s" % (response))
                vals = {"detail": "Not found."}
            else:
                vals = response.text
                _logger.warning("paso %s - Tamaño: %s " % (vals, len(vals)))
                if len(vals) > 40:
                    # En caso de encontrar registro en la API
                    # separo las funcionalidades.
                    # 1. Grabo la info obtenida en variables

                    csx_nombre = self.find_between_r(
                        vals, "[nombre] => ", "[resolucion]"
                    ).rstrip()
                    csx_correoDTE = self.find_between_r(
                        vals, "[correo_dte] => ", "[url]"
                    ).rstrip()
                    csx_web = self.find_between_r(vals, "[url] => ",
                                                  "[fcreado]")
                    csx_pais_id = self.env["res.country"].search(
                        [("code", "=", "CL")], limit=1
                    )
                    csx_dir = (
                        self.find_between_r(vals, "[calle] => ",
                                            "[numero]").rstrip()
                        + " "
                        + self.find_between_r(vals, "[numero] => ",
                                              "[bloque]").rstrip()
                    )
                    csx_dir2 = (
                        self.find_between_r(vals, "[bloque] => ",
                                            "[depto]").rstrip()
                        + " "
                        + self.find_between_r(vals, "[depto] => ",
                                              "[villa]").rstrip()
                    )
                    # 2. Para homologar la comuna, se creo una funcion que
                    # encapsule las validaciones
                    busca_comuna = self._verificar_comuna(vals)
                    self.activity_description = self._buscar_giro(
                        self.find_between_r(vals, "[giro] => ",
                                            "[acteco]").rstrip()
                    )

                    # 3. Verifico si las variables vienen vacia, para no
                    # reemplazar la data que estaalmacenada. Estaba ocurriendo
                    # que si la API regresa un valor en blanco, y la ficha del
                    # contacto tienen información, la misma es reemplazada por
                    # blanco
                    if len(csx_nombre) > 0:
                        # En algunos casos el nombre viene en blanco
                        # No pude reproducir cuando el nombre viene en blanco
                        # pero con esta opción no se debe tener problemas
                        self.name = csx_nombre
                    if len(csx_correoDTE) > 0:
                        self.dte_email = csx_correoDTE
                    if len(csx_web) > 0:
                        self.website = csx_web
                    self.country_id = csx_pais_id
                    # En la data solo hay empresas jurídicas. De todas maneras
                    # por defecto usaremos empresas ya que es lo común
                    self.company_type = "company"
                    # Va contra len > 1 porque aunque no se encuentra
                    # direccion, en la concatenación de las variables,
                    # se agrega un espació en blanco
                    if len(csx_dir) > 1:
                        self.street = csx_dir
                    if len(csx_dir2) > 1:
                        self.street2 = csx_dir2
                    if busca_comuna:
                        self.city_id = busca_comuna.id

        elif self.document_number and (
            "sii.document.type",
            self.document_type_id.id,
        ) == mod_obj.get_object_reference("l10n_cl_electronic_invoicing",
                                          "dt_Sigd"):
            _logger.warning("Borra el document_number")
            self.document_number = ""
        else:
            self.vat = ""

    # Para apoyar el codigo de busqueda de la comuna con respecto a la API_RUT
    def _verificar_comuna(self, registro):
        comuna = (
            self.find_between_r(registro, "[comuna] => ",
                                "[region]").rstrip().lstrip()
        )

        if comuna == "NUNOA":
            comuna = "Ñuñoa"
        elif comuna == "CAMINA":
            comuna = "Camiña"
        elif comuna == "PENALOLEN":
            comuna = "Peñalolén"
        elif comuna == "PENAFLOR":
            comuna = "Peñaflor"
        elif comuna == "VIVUNA":
            comuna = "Vicuña"
        elif comuna == "VINA DEL MAR":
            comuna = "Viña del Mar"
        elif comuna == "DONIHUE":
            comuna = "Doñihue"
        elif comuna == "HUALANE":
            comuna = "Hualañé"
        elif comuna == "CANETE":
            comuna = "Cañete"
        elif comuna == "NIQUEN":
            comuna = "Ñiquén"
        elif comuna == "RIO IBANEZ":
            comuna = "Río Ibáñez"
        elif comuna == "CONCEPCION":
            comuna = "Concepción"
        elif comuna == "CONCHALI":
            comuna = "Conchalí"
        elif comuna == "PUERTO NATALES":
            comuna = "Natales"

        busca_comuna = self.env["res.city"].search(
            [("name", "=", comuna.title())], limit=1
        )
        _logger.warning(
            "Comuna a ser buscada: (%s) - Se encontro: %s"
            % (comuna.title(), busca_comuna)
        )

        return busca_comuna

    @api.onchange("city_id")
    def _asign_city(self):
        if self.city_id:
            self.country_id = self.city_id.state_id.country_id.id
            self.state_id = self.city_id.state_id.id
            self.city = self.city_id.name

    @api.constrains("vat", "commercial_partner_id")
    def _rut_unique(self):
        for r in self:
            if not r.vat or r.parent_id:
                continue
            partner = self.env["res.partner"].search(
                [
                    ("vat", "=", r.vat),
                    ("id", "!=", r.id),
                    ("commercial_partner_id", "!=",
                     r.commercial_partner_id.id),
                ]
            )
            if r.vat != "CL555555555" and partner:
                raise UserError(_("El rut: %s debe ser único") % r.vat)
            return False

    def _buscar_giro(self, registro):
        giro = registro.strip().upper()

        busca_giro = self.env["sii.activity.description"].search(
            [("name", "=", giro)], limit=1)

        giro_retorno = False
        if busca_giro:
            giro_retorno = busca_giro.id
        else:
            # En caso de no encontrar la comuna
            _logger.warning(
                "Giro a ser buscado: (%s) - Se encontro: %s" %
                (giro, busca_giro))
            # -----------------------------------------
            # Si el giro no existe se crea
            # En FE se debe agregar campos que faltan: Ejemplo codigo del sii
            # En el Excel hay que agregar si es: IVA afecto, no o ND
            giro_grabar = {}
            giro_grabar["name"] = giro
            # giro_grabar['vat_affected'] = 'SI'
            # giro_grabar['active'] = True
            # -#_logger.warning("--> Grabar: %s" %(giro_grabar))
            giro_retorno = \
                self.env["sii.activity.description"].create(giro_grabar)
            giro_retorno = giro_retorno.id
            # -#_logger.warning("--> Grabo: %s" %(giro_retorno))
            # -----------------------------------------

        return giro_retorno

    @api.model
    def _arregla_str(self, texto, size=1):
        c = 0
        cadena = ""
        special_chars = [
            [u"á", "a"],
            [u"é", "e"],
            [u"í", "i"],
            [u"ó", "o"],
            [u"ú", "u"],
            [u"ñ", "n"],
            [u"Á", "A"],
            [u"É", "E"],
            [u"Í", "I"],
            [u"Ó", "O"],
            [u"Ú", "U"],
            [u"Ñ", "N"],
        ]

        while c < size and c < len(texto):
            cadena += texto[c]
            c += 1

        for char in special_chars:
            try:
                cadena = cadena.replace(char[0], char[1])
            except:
                pass
        return cadena

    def update_document(self):
        self.onchange_document()

    def check_vat_cl(self, vat):
        body, vdig = "", ""
        if len(vat) != 9:
            return False
        else:
            body, vdig = vat[:-1], vat[-1].upper()
        try:
            vali = list(range(2, 8)) + [2, 3]
            operar = "0123456789K0"[
                11
                - (
                    sum(
                        [int(digit) * factor for digit, factor in
                         zip(body[::-1],
                             vali)]
                    )
                    % 11
                )
            ]
            if operar == vdig:
                return True
            else:
                return False
        except IndexError:
            return False
