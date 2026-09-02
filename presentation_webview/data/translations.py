# Translation tables for SPIKE-001 Content Studio screen.
#
# Owns: user-visible strings for EN and BHS variants of the Content Studio
#       screen (per AI Campaign Studio mockup, screen 4 of 6).
# Does not own: any actual localization framework, fallback chains, or
#               per-platform string registries -- spike is throwaway code.
#
# Strings are taken from the actual mockup attached by the Human Owner
# (product tour + dashboard overview), not invented. BHS variant
# preserves diacritics (č, ć, ž, š, đ) and slightly longer phrasing in
# places where the EN copy is unusually short, to still stress-test
# layout (longer words, more text per line) without making the demo
# content implausibly long.

TRANSLATIONS = {
    "en": {
        "title": "Content Studio",
        "post_counter": "Post 2 of 6",
        "tab_edit": "Edit",
        "tab_notes": "Notes",
        "platform_label": "Instagram - Feed Post - Carousel",
        "preview_alt": "BrightSmile - Oral Care - Science behind your smile.",
        "preview_replace_image": "Replace image",
        "preview_more": "More",
        "headline_label": "Headline",
        "headline_text": "How whitening actually works",
        "headline_max": 80,
        "caption_label": "Caption",
        "caption_text": "Whitening works by breaking down surface stains without damaging enamel. Professional in-chair treatment is faster and longer-lasting than home strips.",
        "caption_max": 220,
        "cta_label": "Call to action",
        "cta_placeholder": "Learn more",
        "hashtags_label": "Hashtags",
        "hashtags_text": "#BrightSmile #TeethWhitening #OralCare",
        "hashtags_placeholder": "Add hashtag",
        "facts_label": "Facts used (3)",
        "facts": [
            {
                "id": 1,
                "text": "Hydrogen peroxide is the active whitening agent in professional dental treatments.",
                "source": "Approved Facts - Brand Library",
            },
            {
                "id": 2,
                "text": "Results typically last 12-24 months with proper maintenance and regular check-ups.",
                "source": "Approved Facts - Clinical Reference",
            },
            {
                "id": 3,
                "text": "Whitening does not damage enamel when performed under the supervision of a licensed dentist.",
                "source": "Approved Facts - Dental Association",
            },
        ],
        "quick_actions_label": "Quick actions",
        "btn_rewrite": "Rewrite",
        "btn_shorten": "Shorten",
        "btn_improve_hook": "Improve hook",
        "btn_change_tone": "Change tone",
        "claim_check_title": "Claim Check",
        "claim_check_status": "All claims supported",
        "claim_check_detail": "Review facts",
        "bottom_notice": "Fact-first content. Human review required before publishing.",
        "btn_save_draft": "Save draft",
        "btn_send_review": "Send for review",
        "exit_btn": "Done",
        "lang_toggle_label": "Language",
        "lang_en": "EN",
        "lang_bs": "BHS",
    },
    "bs": {
        "title": "Studio sadržaja",
        "post_counter": "Post 2 od 6",
        "tab_edit": "Uredi",
        "tab_notes": "Napomene",
        "platform_label": "Instagram - Objava u feedu - Karusel",
        "preview_alt": "BrightSmile - Oral Care - Nauka iza vašeg osmijeha.",
        "preview_replace_image": "Zamijeni sliku",
        "preview_more": "Više",
        "headline_label": "Naslov",
        "headline_text": "Kako izbjeljivanje zaista funkcioniše",
        "headline_max": 80,
        "caption_label": "Opis",
        "caption_text": "Izbjeljivanje djeluje razgradnjom površinskih mrlja bez oštećenja gleđi. Profesionalni tretman u ordinaciji daje brže i postojanije rezultate od kućnih traka.",
        "caption_max": 220,
        "cta_label": "Poziv na akciju",
        "cta_placeholder": "Saznajte više",
        "hashtags_label": "Heštegovi",
        "hashtags_text": "#BrightSmile #IzbjeljivanjeZuba #OralnaHigijena",
        "hashtags_placeholder": "Dodaj hešteg",
        "facts_label": "Korištene činjenice (3)",
        "facts": [
            {
                "id": 1,
                "text": "Vodonik-peroksid je aktivno sredstvo za izbjeljivanje u profesionalnim stomatološkim tretmanima.",
                "source": "Odobrene činjenice - Biblioteka brenda",
            },
            {
                "id": 2,
                "text": "Rezultati u prosjeku traju između 12 i 24 mjeseca uz pravilno održavanje i redovne stomatološke kontrole.",
                "source": "Odobrene činjenice - Klinička referenca",
            },
            {
                "id": 3,
                "text": "Izbjeljivanje ne oštećuje gleđ kada se izvodi pod nadzorom ovlaštenog stomatologa i prema propisanom protokolu.",
                "source": "Odobrene činjenice - Stomatološka asocijacija",
            },
        ],
        "quick_actions_label": "Brze akcije",
        "btn_rewrite": "Prepiši",
        "btn_shorten": "Skraćivanje",
        "btn_improve_hook": "Poboljšaj hook",
        "btn_change_tone": "Promijeni ton",
        "claim_check_title": "Provjera usklađenosti",
        "claim_check_status": "Sadržaj usklađen",
        "claim_check_detail": "Pregledaj činjenice",
        "bottom_notice": "Sadržaj je zasnovan na činjenicama. Zahtijeva ljudsku reviziju prije objavljivanja.",
        "btn_save_draft": "Sačuvaj nacrt",
        "btn_send_review": "Pošalji na reviziju",
        "exit_btn": "Završeno",
        "lang_toggle_label": "Jezik",
        "lang_en": "EN",
        "lang_bs": "BHS",
    },
}


def get(lang: str) -> dict:
    """Return the translation dict for a given language code.

    Spike code: no validation, no fallback chain. Unknown lang -> KeyError
    is fine; the JS layer picks the language from the URL.
    """
    return TRANSLATIONS[lang]
