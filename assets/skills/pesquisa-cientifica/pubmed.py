#!/usr/bin/env python3
"""Busca no PubMed pela API publica do NCBI (E-utilities). So biblioteca padrao.

    python pubmed.py "orthognathic surgery obstructive sleep apnea" --n 8
    python pubmed.py "third molar coronectomy" --n 5 --anos 5

Imprime, por artigo: titulo, autores, revista, ano, PMID, DOI, link e resumo.
E' fonte de VERDADE: so cite artigo que apareceu aqui (ou que voce abriu no
navegador). Referencia inventada em trabalho cientifico e' falha grave.
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
UA = {"User-Agent": "copiloto-cirurgiao/1.0 (contato via consultorio)"}


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def buscar_ids(termo, n, anos=None):
    q = termo
    if anos:
        q = f"({termo}) AND (\"last {anos} years\"[PDat])"
    url = f"{BASE}/esearch.fcgi?db=pubmed&retmode=json&sort=relevance&retmax={n}&term={urllib.parse.quote(q)}"
    dados = json.loads(_get(url))
    return dados.get("esearchresult", {}).get("idlist", [])


def _texto(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip() if el is not None else ""


def detalhar(ids):
    if not ids:
        return []
    url = f"{BASE}/efetch.fcgi?db=pubmed&retmode=xml&id={','.join(ids)}"
    raiz = ET.fromstring(_get(url))
    artigos = []
    for art in raiz.findall(".//PubmedArticle"):
        pmid = _texto(art.find(".//PMID"))
        titulo = _texto(art.find(".//ArticleTitle"))
        revista = _texto(art.find(".//Journal/ISOAbbreviation")) or _texto(art.find(".//Journal/Title"))
        ano = _texto(art.find(".//JournalIssue/PubDate/Year")) or _texto(art.find(".//JournalIssue/PubDate/MedlineDate"))[:4]
        autores = []
        for a in art.findall(".//AuthorList/Author"):
            sobrenome = _texto(a.find("LastName"))
            iniciais = _texto(a.find("Initials"))
            if sobrenome:
                autores.append(f"{sobrenome} {iniciais}".strip())
        resumo_partes = []
        for ab in art.findall(".//Abstract/AbstractText"):
            rotulo = ab.get("Label")
            txt = _texto(ab)
            resumo_partes.append(f"{rotulo}: {txt}" if rotulo else txt)
        doi = ""
        for aid in art.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = _texto(aid)
        tipos = [_texto(t) for t in art.findall(".//PublicationTypeList/PublicationType")]
        artigos.append(
            {
                "pmid": pmid,
                "titulo": titulo,
                "autores": autores,
                "revista": revista,
                "ano": ano,
                "doi": doi,
                "tipos": tipos,
                "resumo": " ".join(resumo_partes),
            }
        )
    return artigos


def vancouver(a):
    autores = a["autores"]
    if len(autores) > 6:
        lista = ", ".join(autores[:6]) + ", et al"
    else:
        lista = ", ".join(autores)
    doi = f" doi:{a['doi']}." if a["doi"] else ""
    return f"{lista}. {a['titulo']} {a['revista']}. {a['ano']}.{doi} PMID: {a['pmid']}."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("termo", help="termos de busca, em inglês (o PubMed é indexado em inglês)")
    ap.add_argument("--n", type=int, default=8, help="quantos artigos (padrão 8)")
    ap.add_argument("--anos", type=int, default=None, help="limitar aos últimos N anos")
    ap.add_argument("--json", action="store_true", help="saída em JSON")
    args = ap.parse_args()

    try:
        ids = buscar_ids(args.termo, args.n, args.anos)
        artigos = detalhar(ids)
    except Exception as e:  # rede fora, NCBI instavel: falha explicita, sem inventar
        print(f"ERRO ao consultar o PubMed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(artigos, ensure_ascii=False, indent=1))
        return 0

    if not artigos:
        print("Nenhum artigo encontrado para esses termos.")
        return 0

    print(f"{len(artigos)} artigos para: {args.termo}\n")
    for i, a in enumerate(artigos, 1):
        print(f"[{i}] {a['titulo']}")
        print(f"    {', '.join(a['autores'][:4])}{' et al' if len(a['autores']) > 4 else ''} — {a['revista']}, {a['ano']}")
        if a["tipos"]:
            marcas = [t for t in a["tipos"] if t in ("Randomized Controlled Trial", "Meta-Analysis", "Systematic Review", "Review", "Case Reports", "Clinical Trial")]
            if marcas:
                print(f"    tipo: {', '.join(marcas)}")
        print(f"    https://pubmed.ncbi.nlm.nih.gov/{a['pmid']}/")
        if a["resumo"]:
            print(f"    resumo: {a['resumo'][:900]}{'...' if len(a['resumo']) > 900 else ''}")
        print(f"    Vancouver: {vancouver(a)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
