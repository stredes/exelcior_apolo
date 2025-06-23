"""
Ventana de consulta por ubicación geográfica.

Permite buscar códigos postales y información geográfica.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Any, List
import json
from pathlib import Path

from ..utils import get_logger

logger = get_logger("exelcior.gui.location_search_window")


class LocationSearchWindow:
    """
    Ventana de consulta por ubicación.
    
    Permite buscar códigos postales por comuna y región.
    """

    def __init__(self, parent: tk.Tk):
        """
        Inicializa la ventana de consulta por ubicación.
        
        Args:
            parent: Ventana padre
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("📍 Consulta por Ubicación")
        self.window.geometry("800x600")
        self.window.transient(parent)
        
        self.postal_codes_data = self._load_postal_codes()
        
        self._create_interface()

    def _load_postal_codes(self) -> Dict[str, Any]:
        """Carga los datos de códigos postales."""
        try:
            # Datos de códigos postales de Chile
            postal_data = {
                "regiones": {
                    "XV": {
                        "nombre": "Arica y Parinacota",
                        "comunas": {
                            "ARICA": {"codigo": "1000000", "poblacion": 221364},
                            "CAMARONES": {"codigo": "1000001", "poblacion": 1233},
                            "PUTRE": {"codigo": "1000002", "poblacion": 2515},
                            "GENERAL LAGOS": {"codigo": "1000003", "poblacion": 810}
                        }
                    },
                    "I": {
                        "nombre": "Tarapacá",
                        "comunas": {
                            "IQUIQUE": {"codigo": "1100000", "poblacion": 191468},
                            "ALTO HOSPICIO": {"codigo": "1100001", "poblacion": 108375},
                            "POZO ALMONTE": {"codigo": "1100002", "poblacion": 17395},
                            "CAMIÑA": {"codigo": "1100003", "poblacion": 1275},
                            "COLCHANE": {"codigo": "1100004", "poblacion": 1583},
                            "HUARA": {"codigo": "1100005", "poblacion": 3000},
                            "PICA": {"codigo": "1100006", "poblacion": 6178}
                        }
                    },
                    "II": {
                        "nombre": "Antofagasta",
                        "comunas": {
                            "ANTOFAGASTA": {"codigo": "2000000", "poblacion": 425725},
                            "MEJILLONES": {"codigo": "2000001", "poblacion": 14776},
                            "SIERRA GORDA": {"codigo": "2000002", "poblacion": 1746},
                            "TALTAL": {"codigo": "2000003", "poblacion": 13317},
                            "CALAMA": {"codigo": "2100000", "poblacion": 190336},
                            "OLLAGÜE": {"codigo": "2100001", "poblacion": 287},
                            "SAN PEDRO DE ATACAMA": {"codigo": "2100002", "poblacion": 10996},
                            "TOCOPILLA": {"codigo": "2200000", "poblacion": 28079},
                            "MARÍA ELENA": {"codigo": "2200001", "poblacion": 5754}
                        }
                    },
                    "III": {
                        "nombre": "Atacama",
                        "comunas": {
                            "COPIAPÓ": {"codigo": "3000000", "poblacion": 171766},
                            "CALDERA": {"codigo": "3000001", "poblacion": 19426},
                            "TIERRA AMARILLA": {"codigo": "3000002", "poblacion": 13384},
                            "CHAÑARAL": {"codigo": "3100000", "poblacion": 13543},
                            "DIEGO DE ALMAGRO": {"codigo": "3100001", "poblacion": 14358},
                            "VALLENAR": {"codigo": "3200000", "poblacion": 57003},
                            "ALTO DEL CARMEN": {"codigo": "3200001", "poblacion": 5729},
                            "FREIRINA": {"codigo": "3200002", "poblacion": 7681},
                            "HUASCO": {"codigo": "3200003", "poblacion": 10691}
                        }
                    },
                    "IV": {
                        "nombre": "Coquimbo",
                        "comunas": {
                            "LA SERENA": {"codigo": "4000000", "poblacion": 249656},
                            "COQUIMBO": {"codigo": "4000001", "poblacion": 227730},
                            "ANDACOLLO": {"codigo": "4000002", "poblacion": 11791},
                            "LA HIGUERA": {"codigo": "4000003", "poblacion": 4450},
                            "PAIGUANO": {"codigo": "4000004", "poblacion": 4675},
                            "VICUÑA": {"codigo": "4000005", "poblacion": 29741},
                            "ILLAPEL": {"codigo": "4100000", "poblacion": 32735},
                            "CANELA": {"codigo": "4100001", "poblacion": 9546},
                            "LOS VILOS": {"codigo": "4100002", "poblacion": 22493},
                            "SALAMANCA": {"codigo": "4100003", "poblacion": 28599},
                            "OVALLE": {"codigo": "4200000", "poblacion": 118594},
                            "COMBARBALÁ": {"codigo": "4200001", "poblacion": 13884},
                            "MONTE PATRIA": {"codigo": "4200002", "poblacion": 31003},
                            "PUNITAQUI": {"codigo": "4200003", "poblacion": 11632},
                            "RÍO HURTADO": {"codigo": "4200004", "poblacion": 4372}
                        }
                    },
                    "V": {
                        "nombre": "Valparaíso",
                        "comunas": {
                            "VALPARAÍSO": {"codigo": "5000000", "poblacion": 296655},
                            "CASABLANCA": {"codigo": "5000001", "poblacion": 29170},
                            "CONCÓN": {"codigo": "5000002", "poblacion": 45889},
                            "JUAN FERNÁNDEZ": {"codigo": "5000003", "poblacion": 633},
                            "PUCHUNCAVÍ": {"codigo": "5000004", "poblacion": 18546},
                            "QUINTERO": {"codigo": "5000005", "poblacion": 31923},
                            "VIÑA DEL MAR": {"codigo": "5000006", "poblacion": 334248},
                            "ISLA DE PASCUA": {"codigo": "5100000", "poblacion": 8277},
                            "LOS ANDES": {"codigo": "5200000", "poblacion": 68093},
                            "CALLE LARGA": {"codigo": "5200001", "poblacion": 12266},
                            "RINCONADA": {"codigo": "5200002", "poblacion": 7287},
                            "SAN ESTEBAN": {"codigo": "5200003", "poblacion": 19299},
                            "LA LIGUA": {"codigo": "5300000", "poblacion": 37739},
                            "CABILDO": {"codigo": "5300001", "poblacion": 20663},
                            "PAPUDO": {"codigo": "5300002", "poblacion": 6000},
                            "PETORCA": {"codigo": "5300003", "poblacion": 10588},
                            "ZAPALLAR": {"codigo": "5300004", "poblacion": 7994},
                            "QUILLOTA": {"codigo": "5400000", "poblacion": 97572},
                            "CALERA": {"codigo": "5400001", "poblacion": 53591},
                            "HIJUELAS": {"codigo": "5400002", "poblacion": 18285},
                            "LA CRUZ": {"codigo": "5400003", "poblacion": 15817},
                            "LIMACHE": {"codigo": "5400004", "poblacion": 48774},
                            "NOGALES": {"codigo": "5400005", "poblacion": 23490},
                            "OLMUÉ": {"codigo": "5400006", "poblacion": 19266},
                            "SAN ANTONIO": {"codigo": "5500000", "poblacion": 94079},
                            "ALGARROBO": {"codigo": "5500001", "poblacion": 15174},
                            "CARTAGENA": {"codigo": "5500002", "poblacion": 25357},
                            "EL QUISCO": {"codigo": "5500003", "poblacion": 17742},
                            "EL TABO": {"codigo": "5500004", "poblacion": 14338},
                            "SANTO DOMINGO": {"codigo": "5500005", "poblacion": 10996},
                            "SAN FELIPE": {"codigo": "5600000", "poblacion": 80888},
                            "CATEMU": {"codigo": "5600001", "poblacion": 14014},
                            "LLAILLAY": {"codigo": "5600002", "poblacion": 25277},
                            "PANQUEHUE": {"codigo": "5600003", "poblacion": 7633},
                            "PUTAENDO": {"codigo": "5600004", "poblacion": 16272},
                            "SANTA MARÍA": {"codigo": "5600005", "poblacion": 15361}
                        }
                    },
                    "RM": {
                        "nombre": "Metropolitana",
                        "comunas": {
                            "SANTIAGO": {"codigo": "8320000", "poblacion": 503147},
                            "CERRILLOS": {"codigo": "8321000", "poblacion": 88956},
                            "CERRO NAVIA": {"codigo": "8322000", "poblacion": 142465},
                            "CONCHALÍ": {"codigo": "8323000", "poblacion": 139195},
                            "EL BOSQUE": {"codigo": "8324000", "poblacion": 162505},
                            "ESTACIÓN CENTRAL": {"codigo": "8325000", "poblacion": 147041},
                            "HUECHURABA": {"codigo": "8326000", "poblacion": 112528},
                            "INDEPENDENCIA": {"codigo": "8327000", "poblacion": 142065},
                            "LA CISTERNA": {"codigo": "8328000", "poblacion": 90119},
                            "LA FLORIDA": {"codigo": "8329000", "poblacion": 402433},
                            "LA GRANJA": {"codigo": "8330000", "poblacion": 122557},
                            "LA PINTANA": {"codigo": "8331000", "poblacion": 189335},
                            "LA REINA": {"codigo": "8332000", "poblacion": 100252},
                            "LAS CONDES": {"codigo": "8333000", "poblacion": 330759},
                            "LO BARNECHEA": {"codigo": "8334000", "poblacion": 124076},
                            "LO ESPEJO": {"codigo": "8335000", "poblacion": 103865},
                            "LO PRADO": {"codigo": "8336000", "poblacion": 104316},
                            "MACUL": {"codigo": "8337000", "poblacion": 134635},
                            "MAIPÚ": {"codigo": "8338000", "poblacion": 578605},
                            "ÑUÑOA": {"codigo": "8339000", "poblacion": 250192},
                            "PEDRO AGUIRRE CERDA": {"codigo": "8340000", "poblacion": 107803},
                            "PEÑALOLÉN": {"codigo": "8341000", "poblacion": 266798},
                            "PROVIDENCIA": {"codigo": "8342000", "poblacion": 142079},
                            "PUDAHUEL": {"codigo": "8343000", "poblacion": 253139},
                            "QUILICURA": {"codigo": "8344000", "poblacion": 254694},
                            "QUINTA NORMAL": {"codigo": "8345000", "poblacion": 136302},
                            "RECOLETA": {"codigo": "8346000", "poblacion": 190075},
                            "RENCA": {"codigo": "8347000", "poblacion": 160847},
                            "SAN JOAQUÍN": {"codigo": "8348000", "poblacion": 103485},
                            "SAN MIGUEL": {"codigo": "8349000", "poblacion": 133059},
                            "SAN RAMÓN": {"codigo": "8350000", "poblacion": 82900},
                            "VITACURA": {"codigo": "8351000", "poblacion": 96774}
                        }
                    },
                    "VI": {
                        "nombre": "O'Higgins",
                        "comunas": {
                            "RANCAGUA": {"codigo": "6000000", "poblacion": 267791},
                            "CODEGUA": {"codigo": "6000001", "poblacion": 13893},
                            "COINCO": {"codigo": "6000002", "poblacion": 7584},
                            "COLTAUCO": {"codigo": "6000003", "poblacion": 21263},
                            "DOÑIHUE": {"codigo": "6000004", "poblacion": 23272},
                            "GRANEROS": {"codigo": "6000005", "poblacion": 35754},
                            "LAS CABRAS": {"codigo": "6000006", "poblacion": 26696},
                            "MACHALÍ": {"codigo": "6000007", "poblacion": 59913},
                            "MALLOA": {"codigo": "6000008", "poblacion": 14656},
                            "MOSTAZAL": {"codigo": "6000009", "poblacion": 27462},
                            "OLIVAR": {"codigo": "6000010", "poblacion": 14626},
                            "PEUMO": {"codigo": "6000011", "poblacion": 15242},
                            "PICHIDEGUA": {"codigo": "6000012", "poblacion": 21138},
                            "QUINTA DE TILCOCO": {"codigo": "6000013", "poblacion": 13294},
                            "RENGO": {"codigo": "6000014", "poblacion": 60533},
                            "REQUÍNOA": {"codigo": "6000015", "poblacion": 31807},
                            "SAN VICENTE": {"codigo": "6000016", "poblacion": 48194}
                        }
                    },
                    "VII": {
                        "nombre": "Maule",
                        "comunas": {
                            "TALCA": {"codigo": "7100000", "poblacion": 236724},
                            "CONSTITUCIÓN": {"codigo": "7100001", "poblacion": 50348},
                            "CUREPTO": {"codigo": "7100002", "poblacion": 9330},
                            "EMPEDRADO": {"codigo": "7100003", "poblacion": 4493},
                            "MAULE": {"codigo": "7100004", "poblacion": 63038},
                            "PELARCO": {"codigo": "7100005", "poblacion": 8838},
                            "PENCAHUE": {"codigo": "7100006", "poblacion": 9357},
                            "RÍO CLARO": {"codigo": "7100007", "poblacion": 14364},
                            "SAN CLEMENTE": {"codigo": "7100008", "poblacion": 44607},
                            "SAN RAFAEL": {"codigo": "7100009", "poblacion": 9997},
                            "CAUQUENES": {"codigo": "7200000", "poblacion": 43076},
                            "CHANCO": {"codigo": "7200001", "poblacion": 9131},
                            "PELLUHUE": {"codigo": "7200002", "poblacion": 8021},
                            "CURICÓ": {"codigo": "7300000", "poblacion": 158438},
                            "HUALAÑÉ": {"codigo": "7300001", "poblacion": 10272},
                            "LICANTÉN": {"codigo": "7300002", "poblacion": 7400},
                            "MOLINA": {"codigo": "7300003", "poblacion": 48442},
                            "RAUCO": {"codigo": "7300004", "poblacion": 10584},
                            "ROMERAL": {"codigo": "7300005", "poblacion": 15123},
                            "SAGRADA FAMILIA": {"codigo": "7300006", "poblacion": 19827},
                            "TENO": {"codigo": "7300007", "poblacion": 31756},
                            "VICHUQUÉN": {"codigo": "7300008", "poblacion": 4427},
                            "LINARES": {"codigo": "7400000", "poblacion": 99780},
                            "COLBÚN": {"codigo": "7400001", "poblacion": 24145},
                            "LONGAVÍ": {"codigo": "7400002", "poblacion": 32445},
                            "PARRAL": {"codigo": "7400003", "poblacion": 42766},
                            "RETIRO": {"codigo": "7400004", "poblacion": 20053},
                            "SAN JAVIER": {"codigo": "7400005", "poblacion": 45822},
                            "VILLA ALEGRE": {"codigo": "7400006", "poblacion": 17676},
                            "YERBAS BUENAS": {"codigo": "7400007", "poblacion": 19063}
                        }
                    },
                    "VIII": {
                        "nombre": "Biobío",
                        "comunas": {
                            "CONCEPCIÓN": {"codigo": "8100000", "poblacion": 238092},
                            "CORONEL": {"codigo": "8100001", "poblacion": 116262},
                            "CHIGUAYANTE": {"codigo": "8100002", "poblacion": 87835},
                            "FLORIDA": {"codigo": "8100003", "poblacion": 11841},
                            "HUALQUI": {"codigo": "8100004", "poblacion": 26201},
                            "LOTA": {"codigo": "8100005", "poblacion": 43535},
                            "PENCO": {"codigo": "8100006", "poblacion": 47367},
                            "SAN PEDRO DE LA PAZ": {"codigo": "8100007", "poblacion": 145906},
                            "SANTA JUANA": {"codigo": "8100008", "poblacion": 13092},
                            "TALCAHUANO": {"codigo": "8100009", "poblacion": 151749},
                            "TOMÉ": {"codigo": "8100010", "poblacion": 54946},
                            "HUALPÉN": {"codigo": "8100011", "poblacion": 95499},
                            "LEBU": {"codigo": "8200000", "poblacion": 25035},
                            "ARAUCO": {"codigo": "8200001", "poblacion": 38679},
                            "CAÑETE": {"codigo": "8200002", "poblacion": 35079},
                            "CONTULMO": {"codigo": "8200003", "poblacion": 6330},
                            "CURANILAHUE": {"codigo": "8200004", "poblacion": 31943},
                            "LOS ÁLAMOS": {"codigo": "8200005", "poblacion": 21851},
                            "TIRÚA": {"codigo": "8200006", "poblacion": 10197},
                            "LOS ÁNGELES": {"codigo": "8300000", "poblacion": 202331},
                            "ANTUCO": {"codigo": "8300001", "poblacion": 4306},
                            "CABRERO": {"codigo": "8300002", "poblacion": 30725},
                            "LAJA": {"codigo": "8300003", "poblacion": 23873},
                            "MULCHÉN": {"codigo": "8300004", "poblacion": 31041},
                            "NACIMIENTO": {"codigo": "8300005", "poblacion": 27944},
                            "NEGRETE": {"codigo": "8300006", "poblacion": 10478},
                            "QUILACO": {"codigo": "8300007", "poblacion": 4421},
                            "QUILLECO": {"codigo": "8300008", "poblacion": 10428},
                            "SAN ROSENDO": {"codigo": "8300009", "poblacion": 3670},
                            "SANTA BÁRBARA": {"codigo": "8300010", "poblacion": 13763},
                            "TUCAPEL": {"codigo": "8300011", "poblacion": 15125},
                            "YUMBEL": {"codigo": "8300012", "poblacion": 22132},
                            "ALTO BIOBÍO": {"codigo": "8300013", "poblacion": 7087},
                            "CHILLÁN": {"codigo": "8400000", "poblacion": 198624},
                            "BULNES": {"codigo": "8400001", "poblacion": 22607},
                            "COBQUECURA": {"codigo": "8400002", "poblacion": 5275},
                            "COELEMU": {"codigo": "8400003", "poblacion": 16845},
                            "COIHUECO": {"codigo": "8400004", "poblacion": 28375},
                            "CHILLÁN VIEJO": {"codigo": "8400005", "poblacion": 33827},
                            "EL CARMEN": {"codigo": "8400006", "poblacion": 12334},
                            "NINHUE": {"codigo": "8400007", "poblacion": 5414},
                            "ÑIQUÉN": {"codigo": "8400008", "poblacion": 11765},
                            "PEMUCO": {"codigo": "8400009", "poblacion": 8822},
                            "PINTO": {"codigo": "8400010", "poblacion": 11880},
                            "PORTEZUELO": {"codigo": "8400011", "poblacion": 5244},
                            "QUILLÓN": {"codigo": "8400012", "poblacion": 18777},
                            "QUIRIHUE": {"codigo": "8400013", "poblacion": 12192},
                            "RÁNQUIL": {"codigo": "8400014", "poblacion": 6261},
                            "SAN CARLOS": {"codigo": "8400015", "poblacion": 56252},
                            "SAN FABIÁN": {"codigo": "8400016", "poblacion": 4654},
                            "SAN IGNACIO": {"codigo": "8400017", "poblacion": 16624},
                            "SAN NICOLÁS": {"codigo": "8400018", "poblacion": 12172},
                            "TREHUACO": {"codigo": "8400019", "poblacion": 5696},
                            "YUNGAY": {"codigo": "8400020", "poblacion": 18596}
                        }
                    },
                    "IX": {
                        "nombre": "Araucanía",
                        "comunas": {
                            "TEMUCO": {"codigo": "9100000", "poblacion": 302931},
                            "CARAHUE": {"codigo": "9100001", "poblacion": 25486},
                            "CHOLCHOL": {"codigo": "9100002", "poblacion": 12341},
                            "CUNCO": {"codigo": "9100003", "poblacion": 18132},
                            "CURARREHUE": {"codigo": "9100004", "poblacion": 7802},
                            "FREIRE": {"codigo": "9100005", "poblacion": 25514},
                            "GALVARINO": {"codigo": "9100006", "poblacion": 12633},
                            "GORBEA": {"codigo": "9100007", "poblacion": 15222},
                            "LAUTARO": {"codigo": "9100008", "poblacion": 40746},
                            "LONCOCHE": {"codigo": "9100009", "poblacion": 24739},
                            "MELIPEUCO": {"codigo": "9100010", "poblacion": 6265},
                            "NUEVA IMPERIAL": {"codigo": "9100011", "poblacion": 33777},
                            "PADRE LAS CASAS": {"codigo": "9100012", "poblacion": 82110},
                            "PERQUENCO": {"codigo": "9100013", "poblacion": 7223},
                            "PITRUFQUÉN": {"codigo": "9100014", "poblacion": 26096},
                            "PUCÓN": {"codigo": "9100015", "poblacion": 28523},
                            "SAAVEDRA": {"codigo": "9100016", "poblacion": 12793},
                            "TEODORO SCHMIDT": {"codigo": "9100017", "poblacion": 15786},
                            "TOLTÉN": {"codigo": "9100018", "poblacion": 10055},
                            "VILCÚN": {"codigo": "9100019", "poblacion": 30766},
                            "VILLARRICA": {"codigo": "9100020", "poblacion": 59103},
                            "ANGOL": {"codigo": "9200000", "poblacion": 56058},
                            "COLLIPULLI": {"codigo": "9200001", "poblacion": 26148},
                            "CURACAUTÍN": {"codigo": "9200002", "poblacion": 18178},
                            "ERCILLA": {"codigo": "9200003", "poblacion": 8458},
                            "LONQUIMAY": {"codigo": "9200004", "poblacion": 11049},
                            "LOS SAUCES": {"codigo": "9200005", "poblacion": 7517},
                            "LUMACO": {"codigo": "9200006", "poblacion": 10050},
                            "PURÉN": {"codigo": "9200007", "poblacion": 12188},
                            "RENAICO": {"codigo": "9200008", "poblacion": 10833},
                            "TRAIGUÉN": {"codigo": "9200009", "poblacion": 19314},
                            "VICTORIA": {"codigo": "9200010", "poblacion": 35467}
                        }
                    },
                    "XIV": {
                        "nombre": "Los Ríos",
                        "comunas": {
                            "VALDIVIA": {"codigo": "10100000", "poblacion": 176774},
                            "CORRAL": {"codigo": "10100001", "poblacion": 5447},
                            "LANCO": {"codigo": "10100002", "poblacion": 17652},
                            "LOS LAGOS": {"codigo": "10100003", "poblacion": 20518},
                            "MÁFIL": {"codigo": "10100004", "poblacion": 7389},
                            "MARIQUINA": {"codigo": "10100005", "poblacion": 23250},
                            "PAILLACO": {"codigo": "10100006", "poblacion": 20798},
                            "PANGUIPULLI": {"codigo": "10100007", "poblacion": 35991},
                            "LA UNIÓN": {"codigo": "10200000", "poblacion": 39447},
                            "FUTRONO": {"codigo": "10200001", "poblacion": 15261},
                            "LAGO RANCO": {"codigo": "10200002", "poblacion": 10292},
                            "RÍO BUENO": {"codigo": "10200003", "poblacion": 32925}
                        }
                    },
                    "X": {
                        "nombre": "Los Lagos",
                        "comunas": {
                            "PUERTO MONTT": {"codigo": "10300000", "poblacion": 269398},
                            "CALBUCO": {"codigo": "10300001", "poblacion": 36744},
                            "COCHAMÓ": {"codigo": "10300002", "poblacion": 4013},
                            "FRESIA": {"codigo": "10300003", "poblacion": 12656},
                            "FRUTILLAR": {"codigo": "10300004", "poblacion": 20223},
                            "LOS MUERMOS": {"codigo": "10300005", "poblacion": 17817},
                            "LLANQUIHUE": {"codigo": "10300006", "poblacion": 18621},
                            "MAULLÍN": {"codigo": "10300007", "poblacion": 14894},
                            "PUERTO VARAS": {"codigo": "10300008", "poblacion": 48620},
                            "CASTRO": {"codigo": "10400000", "poblacion": 47607},
                            "ANCUD": {"codigo": "10400001", "poblacion": 42458},
                            "CHONCHI": {"codigo": "10400002", "poblacion": 13569},
                            "CURACO DE VÉLEZ": {"codigo": "10400003", "poblacion": 4066},
                            "DALCAHUE": {"codigo": "10400004", "poblacion": 15069},
                            "PUQUELDÓN": {"codigo": "10400005", "poblacion": 4201},
                            "QUEILÉN": {"codigo": "10400006", "poblacion": 5543},
                            "QUELLÓN": {"codigo": "10400007", "poblacion": 29309},
                            "QUEMCHI": {"codigo": "10400008", "poblacion": 8783},
                            "QUINCHAO": {"codigo": "10400009", "poblacion": 8298},
                            "OSORNO": {"codigo": "10500000", "poblacion": 173410},
                            "PUERTO OCTAY": {"codigo": "10500001", "poblacion": 9192},
                            "PURRANQUE": {"codigo": "10500002", "poblacion": 21347},
                            "PUYEHUE": {"codigo": "10500003", "poblacion": 11787},
                            "RÍO NEGRO": {"codigo": "10500004", "poblacion": 14275},
                            "SAN JUAN DE LA COSTA": {"codigo": "10500005", "poblacion": 7639},
                            "SAN PABLO": {"codigo": "10500006", "poblacion": 10553},
                            "CHAITÉN": {"codigo": "10600000", "poblacion": 5020},
                            "FUTALEUFÚ": {"codigo": "10600001", "poblacion": 2806},
                            "HUALAIHUÉ": {"codigo": "10600002", "poblacion": 9525},
                            "PALENA": {"codigo": "10600003", "poblacion": 1827}
                        }
                    },
                    "XI": {
                        "nombre": "Aysén",
                        "comunas": {
                            "COYHAIQUE": {"codigo": "11000000", "poblacion": 61210},
                            "LAGO VERDE": {"codigo": "11000001", "poblacion": 924},
                            "AYSÉN": {"codigo": "11100000", "poblacion": 25002},
                            "CISNES": {"codigo": "11100001", "poblacion": 5828},
                            "GUAITECAS": {"codigo": "11100002", "poblacion": 1599},
                            "COCHRANE": {"codigo": "11200000", "poblacion": 3685},
                            "O'HIGGINS": {"codigo": "11200001", "poblacion": 661},
                            "TORTEL": {"codigo": "11200002", "poblacion": 572},
                            "CHILE CHICO": {"codigo": "11300000", "poblacion": 4244},
                            "RÍO IBÁÑEZ": {"codigo": "11300001", "poblacion": 2699}
                        }
                    },
                    "XII": {
                        "nombre": "Magallanes",
                        "comunas": {
                            "PUNTA ARENAS": {"codigo": "12000000", "poblacion": 141984},
                            "LAGUNA BLANCA": {"codigo": "12000001", "poblacion": 264},
                            "RÍO VERDE": {"codigo": "12000002", "poblacion": 185},
                            "SAN GREGORIO": {"codigo": "12000003", "poblacion": 681},
                            "CABO DE HORNOS": {"codigo": "12100000", "poblacion": 2063},
                            "ANTÁRTICA": {"codigo": "12200000", "poblacion": 139},
                            "PORVENIR": {"codigo": "12300000", "poblacion": 6904},
                            "PRIMAVERA": {"codigo": "12300001", "poblacion": 694},
                            "TIMAUKEL": {"codigo": "12300002", "poblacion": 282},
                            "NATALES": {"codigo": "12400000", "poblacion": 23782},
                            "TORRES DEL PAINE": {"codigo": "12400001", "poblacion": 1021}
                        }
                    }
                }
            }
            
            return postal_data
            
        except Exception as e:
            logger.error(f"Error cargando códigos postales: {e}")
            return {"regiones": {}}

    def _create_interface(self) -> None:
        """Crea la interfaz de consulta por ubicación."""
        # Frame principal
        main_frame = ttk.Frame(self.window, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title_label = tk.Label(
            main_frame,
            text="📍 Consulta por Ubicación",
            font=("Arial", 16, "bold"),
            fg="#2C3E50"
        )
        title_label.pack(pady=(0, 20))
        
        # Frame de búsqueda
        self._create_search_frame(main_frame)
        
        # Frame de resultados
        self._create_results_frame(main_frame)
        
        # Frame de información
        self._create_info_frame(main_frame)
        
        # Frame de botones
        self._create_buttons_frame(main_frame)

    def _create_search_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de búsqueda."""
        search_frame = ttk.LabelFrame(parent, text="Búsqueda de Ubicación", padding=15)
        search_frame.pack(fill="x", pady=(0, 15))
        
        # Primera fila - Búsqueda por comuna
        row1_frame = ttk.Frame(search_frame)
        row1_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(row1_frame, text="Comuna:").pack(side="left", padx=(0, 10))
        
        self.comuna_var = tk.StringVar()
        comuna_entry = ttk.Entry(row1_frame, textvariable=self.comuna_var, width=25, font=("Arial", 11))
        comuna_entry.pack(side="left", padx=(0, 10))
        comuna_entry.bind("<KeyRelease>", self._on_comuna_change)
        comuna_entry.bind("<Return>", lambda e: self._search_location())
        
        ttk.Button(row1_frame, text="🔍 Buscar", command=self._search_location, width=10).pack(side="left", padx=(0, 5))
        ttk.Button(row1_frame, text="📋 Copiar código", command=self._copy_postal_code, width=15).pack(side="left")
        
        # Segunda fila - Filtros
        row2_frame = ttk.Frame(search_frame)
        row2_frame.pack(fill="x")
        
        ttk.Label(row2_frame, text="Región:").pack(side="left", padx=(0, 10))
        
        self.region_var = tk.StringVar()
        region_values = ["Todas"] + [f"{code} - {data['nombre']}" for code, data in self.postal_codes_data["regiones"].items()]
        region_combo = ttk.Combobox(row2_frame, textvariable=self.region_var, values=region_values, width=30, state="readonly")
        region_combo.set("Todas")
        region_combo.pack(side="left", padx=(0, 15))
        region_combo.bind("<<ComboboxSelected>>", self._on_region_change)
        
        # Opciones de búsqueda
        self.exact_match_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row2_frame, text="Búsqueda exacta", variable=self.exact_match_var).pack(side="left", padx=(15, 0))

    def _create_results_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de resultados."""
        results_frame = ttk.LabelFrame(parent, text="Resultados", padding=15)
        results_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Tabla de resultados
        columns = ("Comuna", "Región", "Código Postal", "Población")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=12)
        
        # Configurar columnas
        column_widths = {"Comuna": 200, "Región": 200, "Código Postal": 120, "Población": 100}
        
        for col in columns:
            self.results_tree.heading(col, text=col, command=lambda c=col: self._sort_results(c))
            self.results_tree.column(col, width=column_widths.get(col, 100), anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        
        self.results_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack elementos
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self.results_tree.pack(side="left", fill="both", expand=True)
        
        # Eventos
        self.results_tree.bind("<Double-1>", self._on_double_click)
        
        # Información de resultados
        self.results_info_label = tk.Label(results_frame, text="", fg="#666666")
        self.results_info_label.pack(side="bottom", anchor="w", pady=(5, 0))

    def _create_info_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de información detallada."""
        self.info_frame = ttk.LabelFrame(parent, text="Información Detallada", padding=15)
        self.info_frame.pack(fill="x", pady=(0, 15))
        
        # Inicialmente vacío, se llena al seleccionar una comuna
        self.info_text = tk.Text(self.info_frame, height=4, wrap="word", state="disabled")
        self.info_text.pack(fill="x")

    def _create_buttons_frame(self, parent: ttk.Frame) -> None:
        """Crea el frame de botones."""
        buttons_frame = ttk.Frame(parent)
        buttons_frame.pack(fill="x")
        
        ttk.Button(buttons_frame, text="📤 Exportar", command=self._export_results, width=12).pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="🔄 Limpiar", command=self._clear_search, width=10).pack(side="left", padx=(0, 10))
        ttk.Button(buttons_frame, text="❌ Cerrar", command=self.window.destroy, width=10).pack(side="right")

    def _on_comuna_change(self, event=None) -> None:
        """Maneja cambios en el campo de comuna."""
        # Búsqueda automática después de una pausa
        self.window.after(500, self._search_location)

    def _on_region_change(self, event=None) -> None:
        """Maneja cambios en la selección de región."""
        self._search_location()

    def _search_location(self) -> None:
        """Realiza la búsqueda de ubicación."""
        try:
            search_comuna = self.comuna_var.get().strip().upper()
            
            if not search_comuna:
                return
            
            # Limpiar resultados anteriores
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            
            # Realizar búsqueda
            results = self._perform_location_search(search_comuna)
            
            # Mostrar resultados
            if results:
                for result in results:
                    self.results_tree.insert("", "end", values=result)
                
                self.results_info_label.config(text=f"Se encontraron {len(results)} resultado(s)")
                
                # Si hay un solo resultado, mostrar información detallada
                if len(results) == 1:
                    self._show_detailed_info(results[0])
            else:
                self.results_info_label.config(text="No se encontraron resultados")
                self._clear_detailed_info()
            
        except Exception as e:
            logger.error(f"Error en búsqueda de ubicación: {e}")
            messagebox.showerror("Error", f"Error al buscar ubicación: {str(e)}")

    def _perform_location_search(self, search_comuna: str) -> List[tuple]:
        """Realiza la búsqueda en los datos de códigos postales."""
        try:
            results = []
            exact_match = self.exact_match_var.get()
            region_filter = self.region_var.get()
            
            # Extraer código de región del filtro
            region_code = None
            if region_filter != "Todas":
                region_code = region_filter.split(" - ")[0]
            
            # Buscar en todas las regiones
            for reg_code, region_data in self.postal_codes_data["regiones"].items():
                # Filtrar por región si está seleccionada
                if region_code and reg_code != region_code:
                    continue
                
                region_name = region_data["nombre"]
                
                # Buscar en comunas de esta región
                for comuna_name, comuna_data in region_data["comunas"].items():
                    # Aplicar filtro de búsqueda
                    if exact_match:
                        if comuna_name == search_comuna:
                            results.append((
                                comuna_name,
                                f"{reg_code} - {region_name}",
                                comuna_data["codigo"],
                                f"{comuna_data['poblacion']:,}"
                            ))
                    else:
                        if search_comuna in comuna_name:
                            results.append((
                                comuna_name,
                                f"{reg_code} - {region_name}",
                                comuna_data["codigo"],
                                f"{comuna_data['poblacion']:,}"
                            ))
            
            # Ordenar resultados por nombre de comuna
            results.sort(key=lambda x: x[0])
            
            return results
            
        except Exception as e:
            logger.error(f"Error realizando búsqueda de ubicación: {e}")
            return []

    def _show_detailed_info(self, result: tuple) -> None:
        """Muestra información detallada de una comuna."""
        try:
            comuna, region, codigo, poblacion = result
            
            # Buscar información adicional
            region_code = region.split(" - ")[0]
            region_data = self.postal_codes_data["regiones"].get(region_code, {})
            comuna_data = region_data.get("comunas", {}).get(comuna, {})
            
            info_text = f"""
📍 {comuna}
🏛️ Región: {region}
📮 Código Postal: {codigo}
👥 Población: {poblacion} habitantes

ℹ️ Información adicional:
• Región administrativa: {region_code}
• Tipo: Comuna
• País: Chile
• Zona horaria: UTC-3 (UTC-4 en invierno)
            """.strip()
            
            self.info_text.config(state="normal")
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info_text)
            self.info_text.config(state="disabled")
            
        except Exception as e:
            logger.error(f"Error mostrando información detallada: {e}")

    def _clear_detailed_info(self) -> None:
        """Limpia la información detallada."""
        self.info_text.config(state="normal")
        self.info_text.delete(1.0, tk.END)
        self.info_text.config(state="disabled")

    def _clear_search(self) -> None:
        """Limpia la búsqueda."""
        self.comuna_var.set("")
        self.region_var.set("Todas")
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.results_info_label.config(text="")
        self._clear_detailed_info()

    def _sort_results(self, column: str) -> None:
        """Ordena los resultados por columna."""
        try:
            # Obtener datos actuales
            data = [(self.results_tree.set(child, column), child) for child in self.results_tree.get_children("")]
            
            # Ordenar
            data.sort(reverse=False)
            
            # Reorganizar elementos
            for index, (val, child) in enumerate(data):
                self.results_tree.move(child, "", index)
                
        except Exception as e:
            logger.error(f"Error ordenando resultados: {e}")

    def _on_double_click(self, event) -> None:
        """Maneja doble click en resultado."""
        selection = self.results_tree.selection()
        if selection:
            item = selection[0]
            values = self.results_tree.item(item, "values")
            self._show_detailed_info(values)

    def _copy_postal_code(self) -> None:
        """Copia el código postal seleccionado al portapapeles."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Selección", "Seleccione una comuna para copiar su código postal")
            return
        
        item = selection[0]
        codigo = self.results_tree.item(item, "values")[2]
        
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(codigo)
            messagebox.showinfo("Copiado", f"Código postal copiado: {codigo}")
        except Exception as e:
            logger.error(f"Error copiando código postal: {e}")

    def _export_results(self) -> None:
        """Exporta los resultados."""
        try:
            from tkinter import filedialog
            import csv
            
            if not self.results_tree.get_children():
                messagebox.showwarning("Sin datos", "No hay resultados para exportar")
                return
            
            file_path = filedialog.asksaveasfilename(
                title="Exportar Resultados",
                defaultextension=".csv",
                filetypes=[("Archivos CSV", "*.csv"), ("Archivos Excel", "*.xlsx")]
            )
            
            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Escribir encabezados
                    headers = ["Comuna", "Región", "Código Postal", "Población"]
                    writer.writerow(headers)
                    
                    # Escribir datos
                    for item in self.results_tree.get_children():
                        values = self.results_tree.item(item, "values")
                        writer.writerow(values)
                
                messagebox.showinfo("Éxito", f"Resultados exportados a: {file_path}")
                
        except Exception as e:
            logger.error(f"Error exportando resultados: {e}")
            messagebox.showerror("Error", f"Error al exportar: {str(e)}")


def open_location_search_window(parent: tk.Tk) -> None:
    """
    Abre la ventana de consulta por ubicación.
    
    Args:
        parent: Ventana padre
    """
    try:
        LocationSearchWindow(parent)
    except Exception as e:
        logger.error(f"Error abriendo ventana de ubicación: {e}")
        messagebox.showerror("Error", f"Error al abrir consulta de ubicación: {str(e)}")

