from app.services.sources.computrabajo import ComputrabajoSource


def test_parse_computrabajo_search_article():
    html = """
    <article class="box_offer" data-id="ABC123">
      <h2><a href="/ofertas-de-trabajo/oferta-de-trabajo-de-backend-en-bogota-ABC123#lc=test">
        Desarrollador Backend
      </a></h2>
      <p class="dFlex vm_fx fs16 fc_base mt5">
        <a offer-grid-article-company-url href="https://co.computrabajo.com/acme">Acme SAS</a>
      </p>
      <p class="fs16 fc_base mt5"><span class="mr10">Bogotá, D.C., Bogotá, D.C.</span></p>
      <p class="fs13 fc_aux mt15">Hace 2 días</p>
    </article>
    """
    jobs = ComputrabajoSource._parse_articles(html, "https://www.computrabajo.com.co/trabajo-de-backend-en-bogota")
    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Desarrollador Backend"
    assert job["company"] == "Acme SAS"
    assert job["location_text"] == "Bogotá, D.C., Bogotá, D.C."
    assert job["url"].startswith("https://www.computrabajo.com.co/ofertas-de-trabajo/")
    assert job["requires_login"] is True
    assert job["posted_at"] is not None


def test_relevance_filter_excludes_sales_titles():
    from app.services.sources.computrabajo import _is_relevant_title

    assert _is_relevant_title("Desarrollador Backend SQL server (.NET)")
    assert _is_relevant_title("Desarrollador(a) Full Stack Junior")
    assert not _is_relevant_title("Desarrollador Comercial // Moto propia")
    assert not _is_relevant_title("Desarrollador de Cuenta Global Wine & Spirits")
    assert not _is_relevant_title("Desarrollador Nacional Canal Off Trade Bogotá")
