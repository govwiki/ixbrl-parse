from bs4 import BeautifulSoup

from ixbrlparse.components import ixbrlContext, ixbrlNonNumeric, ixbrlNumeric

FILETYPE_IXBRL = "ixbrl"
FILETYPE_XBRL = "xbrl"


class IXBRLParser:
    root_element = "html"

    def __init__(self, soup, raise_on_error=True):
        self.soup = soup
        self.raise_on_error = raise_on_error
        self.errors = []

    def _get_schema(self):
        self.schema = self.soup.find(["link:schemaRef", "schemaRef"]).get("xlink:href")
        self.namespaces = {}
        for k in self.soup.find(self.root_element).attrs:
            if k.startswith("xmlns") or ":" in k:
                self.namespaces[k] = self.soup.find(self.root_element)[k].split(" ")

    def _get_context_elements(self):
        resources = self.soup.find(["ix:resources", "resources"])
        for s in resources.find_all(["xbrli:context", "context"]):
            yield s

    def _get_contexts(self):
        self.contexts = {}
        for s in self._get_context_elements():
            self.contexts[s["id"]] = ixbrlContext(
                **{
                    "_id": s["id"],
                    "entity": {
                        "scheme": s.find(["xbrli:identifier", "identifier"])[
                            "scheme"
                        ].strip()
                        if s.find(["xbrli:identifier", "identifier"])
                        else None,
                        "identifier": s.find(
                            ["xbrli:identifier", "identifier"]
                        ).text.strip()
                        if s.find(["xbrli:identifier", "identifier"])
                        else None,
                    },
                    "segments": [
                        {"tag": x.name, "value": x.text.strip(), **x.attrs}
                        for x in s.find(["xbrli:segment", "segment"]).findChildren()
                    ]
                    if s.find(["xbrli:segment", "segment"])
                    else None,
                    "instant": s.find(["xbrli:instant", "instant"]).text.strip()
                    if s.find(["xbrli:instant", "instant"])
                    else None,
                    "startdate": s.find(["xbrli:startDate", "startDate"]).text.strip()
                    if s.find(["xbrli:startDate", "startDate"])
                    else None,
                    "enddate": s.find(["xbrli:endDate", "endDate"]).text.strip()
                    if s.find(["xbrli:endDate", "endDate"])
                    else None,
                }
            )

    def _get_unit_elements(self):
        resources = self.soup.find(["ix:resources", "resources"])
        for s in resources.find_all(["xbrli:unit", "unit"]):
            yield s

    def _get_units(self):
        self.units = {}
        for s in self._get_unit_elements():
            self.units[s["id"]] = (
                s.find(["xbrli:measure", "measure"]).text.strip()
                if s.find(["xbrli:measure", "measure"])
                else None
            )

    def _get_nonnumeric(self):
        self.nonnumeric = []
        for s in self.soup.find_all({"nonNumeric"}):
            element = {
                "context": self.contexts.get(s["contextRef"], s["contextRef"]),
                "name": s["name"],
                "format_": s.get("format"),
                "value": s.text.strip().replace("\n", ""),
            }
            try:
                self.nonnumeric.append(ixbrlNonNumeric(**element))
            except Exception as e:
                self.errors.append(
                    {
                        "error": e,
                        "element": s,
                    }
                )
                if self.raise_on_error:
                    raise

    def _get_numeric(self):
        self.numeric = []
        for s in self.soup.find_all({"nonFraction"}):
            element = {
                "text": s.text,
                "context": self.contexts.get(s["contextRef"], s["contextRef"]),
                "unit": self.units.get(s["unitRef"], s["unitRef"]),
                **s.attrs,
            }
            try:
                self.numeric.append(ixbrlNumeric(element))
            except Exception as e:
                self.errors.append(
                    {
                        "error": e,
                        "element": s,
                    }
                )
                if self.raise_on_error:
                    raise


class XBRLParser(IXBRLParser):
    root_element = "xbrl"

    def _get_context_elements(self):
        for s in self.soup.find_all(["xbrli:context", "context"]):
            yield s

    def _get_unit_elements(self):
        for s in self.soup.find_all(["xbrli:unit", "unit"]):
            yield s

    def _get_elements(self):
        for s in self.soup.find(self.root_element).find_all():
            yield s

    def _get_numeric(self):
        self.numeric = []
        for s in self._get_elements():
            if not s.get("contextRef") or not s.get("unitRef"):
                continue
            element = {
                "name": s.name,
                "text": s.text,
                "context": self.contexts.get(s["contextRef"], s["contextRef"]),
                "unit": self.units.get(s["unitRef"], s["unitRef"]),
                **s.attrs,
            }
            try:
                self.numeric.append(ixbrlNumeric(element))
            except Exception as e:
                self.errors.append(
                    {
                        "error": e,
                        "element": s,
                    }
                )
                if self.raise_on_error:
                    raise

    def _get_nonnumeric(self):
        self.nonnumeric = []
        for s in self._get_elements():
            if not s.get("contextRef") or s.get("unitRef"):
                continue
            element = {
                "context": self.contexts.get(s["contextRef"], s["contextRef"]),
                "name": s.name,
                "format_": s.get("format"),
                "value": s.text.strip().replace("\n", ""),
            }
            try:
                self.nonnumeric.append(ixbrlNonNumeric(**element))
            except Exception as e:
                self.errors.append(
                    {
                        "error": e,
                        "element": s,
                    }
                )
                if self.raise_on_error:
                    raise


class IXBRL:
    def __init__(self, f, raise_on_error=True):
        self.soup = BeautifulSoup(f.read(), "xml")
        self.raise_on_error = raise_on_error
        self._get_parser()
        self.parser._get_schema()
        self.parser._get_contexts()
        self.parser._get_units()
        self.parser._get_nonnumeric()
        self.parser._get_numeric()

    @classmethod
    def open(cls, filename, raise_on_error=True):
        with open(filename, "rb") as a:
            return cls(a, raise_on_error=raise_on_error)

    def _get_parser(self):
        if self.soup.find("html"):
            self.filetype = FILETYPE_IXBRL
            parser = IXBRLParser
        elif self.soup.find("xbrl"):
            self.filetype = FILETYPE_XBRL
            parser = XBRLParser
        else:
            raise Exception("Filetype not recognised")
        self.parser = parser(self.soup, raise_on_error=self.raise_on_error)

    def __getattr__(self, name):
        return getattr(self.parser, name)

    def to_json(self):
        return {
            "schema": self.schema,
            "namespaces": self.namespaces,
            "contexts": {c: ct.to_json() for c, ct in self.contexts.items()},
            "units": self.units,
            "nonnumeric": [a.to_json() for a in self.nonnumeric],
            "numeric": [a.to_json() for a in self.numeric],
            "errors": len(self.errors),
        }

    def to_table(self, fields="numeric"):
        if fields == "nonnumeric":
            values = self.nonnumeric
        elif fields == "numeric":
            values = self.numeric
        else:
            values = self.nonnumeric + self.numeric

        ret = []
        for v in values:
            if v.context.segments:
                segments = {
                    "segment:{}".format(i): "{} {} {}".format(
                        s.get("tag", ""), s.get("dimension"), s.get("value")
                    ).strip()
                    for i, s in enumerate(v.context.segments)
                }
            else:
                segments = {"segment:0": ""}

            ret.append(
                {
                    "schema": " ".join(
                        self.namespaces.get("xmlns:{}".format(v.schema), [v.schema])
                    ),
                    "name": v.name,
                    "value": v.value,
                    "unit": v.unit if hasattr(v, "unit") else None,
                    "instant": str(v.context.instant) if v.context.instant else None,
                    "startdate": str(v.context.startdate)
                    if v.context.startdate
                    else None,
                    "enddate": str(v.context.enddate) if v.context.enddate else None,
                    **segments,
                }
            )
        return ret
