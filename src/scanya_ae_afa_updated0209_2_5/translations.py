"""Texts of the user interface in English, Catalan and German (constants and one lookup, no Streamlit code).

Every text the pages show is a key of TEXTS with one version per language, in the order of
LANGUAGES. Texts may contain {placeholders}, filled in by text(). The pages look texts up
through language.t(), which knows the language the user picked.

What is NOT translated here:
- the documents and the answers: the chat model answers in the language of the question
  (prompts.SYSTEM_PROMPT), and the guard gives its reason in the interface language;
- the prompts and the tool messages: they are read by the models, not shown as interface;
- rare technical error messages that come from libraries or from the logic modules.

To add a language: add it to LANGUAGES and LANGUAGE_NAMES, add one more version to every
entry of TEXTS (the test test_translations.py checks that none is missing), and add its
names and descriptions to categories.toml.

Public: LANGUAGES, DEFAULT_LANGUAGE, LANGUAGE_NAMES, TEXTS, text().
"""

# Language codes, in the order of the versions in TEXTS, and of the flags in the sidebar.
LANGUAGES = ("en", "ca", "de")
DEFAULT_LANGUAGE = "en"
# Name of each language in English, as told to the guard model ("give the reason in Catalan").
LANGUAGE_NAMES = {"en": "English", "ca": "Catalan", "de": "German"}

# Key -> (English, Catalan, German).
TEXTS = {
    # --- App (app.py) ---
    "page_title": ("Building Rules Assistant", "Assistent de normativa d'edificació", "Assistent für Bauvorschriften"),
    "nav_assistant": ("Assistant", "Assistent", "Assistent"),
    "nav_library": ("Knowledge base", "Base de coneixement", "Wissensbasis"),
    "nav_history": ("My history", "El meu historial", "Mein Verlauf"),
    "language": ("Language", "Idioma", "Sprache"),
    # --- Login (auth.py) ---
    "signed_in_as": ("Signed in as **{user}**", "Sessió iniciada com a **{user}**", "Angemeldet als **{user}**"),
    "logout": ("Log out", "Surt", "Abmelden"),
    "login_box": ("Log in or create an account", "Inicia la sessió o crea un compte", "Anmelden oder Konto erstellen"),
    "login_optional": (
        "Optional. Logged in, your conversations and work products are saved in *My history*.",
        "Opcional. Amb la sessió iniciada, les teves converses i documents es desen a *El meu historial*.",
        "Optional. Wenn Sie angemeldet sind, werden Ihre Unterhaltungen und Arbeitsergebnisse in *Mein Verlauf* gespeichert.",
    ),
    "login": ("Log in", "Inicia la sessió", "Anmelden"),
    "create_account": ("Create account", "Crea un compte", "Konto erstellen"),
    "username": ("Username", "Nom d'usuari", "Benutzername"),
    "password": ("Password", "Contrasenya", "Passwort"),
    "repeat_password": ("Repeat password", "Repeteix la contrasenya", "Passwort wiederholen"),
    "first_name": ("First name", "Nom", "Vorname"),
    "last_name": ("Last name", "Cognoms", "Nachname"),
    "email": ("Email", "Correu electrònic", "E-Mail"),
    "any_password": (
        "Any password is accepted for now.",
        "De moment s'accepta qualsevol contrasenya.",
        "Vorerst wird jedes Passwort akzeptiert.",
    ),
    "login_wrong": (
        "Username or password is incorrect.",
        "El nom d'usuari o la contrasenya no són correctes.",
        "Benutzername oder Passwort ist falsch.",
    ),
    "signup_temporary": (
        "Accounts created here only work until the app restarts: the account and its saved "
        "conversations do not persist. For a permanent account, contact the admin.",
        "Els comptes creats aquí només funcionen fins que l'aplicació es reinicia: el compte i les "
        "converses desades no es conserven. Per a un compte permanent, contacta amb l'administrador.",
        "Hier erstellte Konten gelten nur bis zum nächsten Neustart der App: Das Konto und seine "
        "gespeicherten Unterhaltungen bleiben nicht erhalten. Für ein dauerhaftes Konto wenden Sie "
        "sich an den Administrator.",
    ),
    "account_created": (
        "Account **{user}** created. You can now log in.",
        "S'ha creat el compte **{user}**. Ja pots iniciar la sessió.",
        "Konto **{user}** erstellt. Sie können sich jetzt anmelden.",
    ),
    "login_hint": (
        "Log in to save your conversations and keep a total cost.",
        "Inicia la sessió per desar les converses i portar el compte del cost total.",
        "Melden Sie sich an, um Ihre Unterhaltungen zu speichern und die Gesamtkosten zu sehen.",
    ),
    # --- Assistant page: project input (page_chat.py) ---
    "project_input": ("Project input", "Dades del projecte", "Projektangaben"),
    "one_file": ("1 file", "1 fitxer", "1 Datei"),
    "n_files": ("{count} files", "{count} fitxers", "{count} Dateien"),
    "notes": ("notes", "notes", "Notizen"),
    "empty": ("empty", "buit", "leer"),
    "project_files": ("Project files", "Fitxers del projecte", "Projektdateien"),
    "project_files_help": (
        "Drafts, requirement lists or notes about your project. The assistant reads them with "
        "every question. They are not added to the knowledge base.",
        "Esborranys, llistes de requisits o notes sobre el teu projecte. L'assistent els llegeix a "
        "cada pregunta. No s'afegeixen a la base de coneixement.",
        "Entwürfe, Anforderungslisten oder Notizen zu Ihrem Projekt. Der Assistent liest sie bei "
        "jeder Frage mit. Sie werden nicht in die Wissensbasis aufgenommen.",
    ),
    "characters": ("{count} characters", "{count} caràcters", "{count} Zeichen"),
    "remove_project_file": (
        "Remove this file from the project input",
        "Treu aquest fitxer de les dades del projecte",
        "Diese Datei aus den Projektangaben entfernen",
    ),
    "notes_label": ("Notes or requirements", "Notes o requisits", "Notizen oder Anforderungen"),
    "notes_placeholder": (
        "e.g. Hotel with 40 rooms, 4 storeys, restaurant on the ground floor",
        "p. ex. Hotel de 40 habitacions, 4 plantes, restaurant a la planta baixa",
        "z. B. Hotel mit 40 Zimmern, 4 Geschosse, Restaurant im Erdgeschoss",
    ),
    "project_input_cut": (
        "The project input is longer than {limit} characters. The assistant only sees the beginning.",
        "Les dades del projecte tenen més de {limit} caràcters. L'assistent només en veu el principi.",
        "Die Projektangaben sind länger als {limit} Zeichen. Der Assistent sieht nur den Anfang.",
    ),
    # --- Assistant page: documents to search ---
    "documents_to_search": ("Documents to search", "Documents on cercar", "Zu durchsuchende Dokumente"),
    "search_method": ("Search method", "Mètode de cerca", "Suchmethode"),
    "hybrid_search": ("Hybrid search", "Cerca híbrida", "Hybride Suche"),
    "hybrid_help": (
        "On: search by meaning and by exact words (article numbers, standards, values). Off: search by meaning only.",
        "Activada: cerca pel significat i per paraules exactes (números d'article, normes, valors). "
        "Desactivada: només pel significat.",
        "Ein: Suche nach Bedeutung und nach exakten Wörtern (Artikelnummern, Normen, Werte). Aus: nur nach Bedeutung.",
    ),
    # --- Assistant page: chat settings and costs ---
    "model": ("Model", "Model", "Modell"),
    "no_price": ("no price", "sense preu", "kein Preis"),
    "model_help": (
        "With each model: what one typical answer would cost at OpenRouter's prices. Typical means "
        "about {input} input and {output} output tokens over all requests of the answer. What this "
        "chat really cost is in the line below.",
        "Amb cada model: el que costaria una resposta típica als preus d'OpenRouter. Típica vol dir "
        "uns {input} tokens d'entrada i {output} de sortida entre totes les peticions de la resposta. "
        "El cost real d'aquest xat és a la línia de sota.",
        "Bei jedem Modell: was eine typische Antwort zu den Preisen von OpenRouter kosten würde. "
        "Typisch heißt etwa {input} Eingabe- und {output} Ausgabe-Tokens über alle Anfragen der "
        "Antwort. Was dieser Chat wirklich gekostet hat, steht in der Zeile darunter.",
    ),
    "passages_range": ("Passages (1–{max})", "Fragments (1–{max})", "Passagen (1–{max})"),
    "passages_help": (
        "Passages per search: how many passages the assistant is given each time it searches. More "
        "passages can catch a rule that would be missed, but cost more tokens and can distract the "
        "model. The Search steps tab shows the passages of every search.",
        "Fragments per cerca: quants fragments rep l'assistent cada vegada que cerca. Més fragments "
        "poden trobar una norma que s'escaparia, però costen més tokens i poden distreure el model. "
        "La pestanya Passos de cerca mostra els fragments de cada cerca.",
        "Passagen pro Suche: wie viele Passagen der Assistent bei jeder Suche erhält. Mehr Passagen "
        "können eine sonst übersehene Vorschrift finden, kosten aber mehr Tokens und können das "
        "Modell ablenken. Der Reiter Suchschritte zeigt die Passagen jeder Suche.",
    ),
    "searches_range": ("Searches (1–{max})", "Cerques (1–{max})", "Suchen (1–{max})"),
    "searches_help": (
        "Searches per answer: how often the assistant may search for one answer. After reading the "
        "passages of a search it can search again (other words, an article the passages refer to). "
        "More searches can find more, but every search is one more request to the model. Re-reading "
        "passages found earlier in the chat does not count as a search.",
        "Cerques per resposta: quantes vegades pot cercar l'assistent per a una resposta. Després de "
        "llegir els fragments d'una cerca pot tornar a cercar (altres paraules, un article al qual "
        "remeten). Més cerques poden trobar més, però cada cerca és una petició més al model. "
        "Rellegir fragments trobats abans en el xat no compta com a cerca.",
        "Suchen pro Antwort: wie oft der Assistent für eine Antwort suchen darf. Nach dem Lesen der "
        "Passagen einer Suche kann er erneut suchen (andere Wörter, ein Artikel, auf den die "
        "Passagen verweisen). Mehr Suchen finden mehr, aber jede Suche ist eine weitere Anfrage an "
        "das Modell. Das erneute Lesen früher gefundener Passagen zählt nicht als Suche.",
    ),
    "costs_line": (
        "This chat: **{cost}** · {tokens} tokens · Spent: **{spent}** / max {limit}",
        "Aquest xat: **{cost}** · {tokens} tokens · Gastat: **{spent}** / màx. {limit}",
        "Dieser Chat: **{cost}** · {tokens} Tokens · Ausgegeben: **{spent}** / max. {limit}",
    ),
    "cost_details": ("Cost details", "Detall del cost", "Kostendetails"),
    "cost_explanation": (
        "Estimate in US dollars. Every request to a chat model is counted with the price of the "
        "model that answered it: the cost OpenRouter reports, or else tokens × the model's price per "
        "token. The embedding of each search query is counted too, under the embedding model.",
        "Estimació en dòlars dels EUA. Cada petició a un model de xat es compta amb el preu del model "
        "que l'ha resposta: el cost que informa OpenRouter o, si no, tokens × el preu per token del "
        "model. L'embedding de cada consulta de cerca també es compta, sota el model d'embeddings.",
        "Schätzung in US-Dollar. Jede Anfrage an ein Chatmodell wird mit dem Preis des Modells "
        "gezählt, das sie beantwortet hat: die von OpenRouter gemeldeten Kosten, sonst Tokens × "
        "Preis pro Token des Modells. Das Embedding jeder Suchanfrage wird ebenfalls gezählt, unter "
        "dem Embedding-Modell.",
    ),
    "cost_model_line": (
        "{model}: {cost} · {requests} requests · {input} in / {output} out",
        "{model}: {cost} · {requests} peticions · {input} d'entrada / {output} de sortida",
        "{model}: {cost} · {requests} Anfragen · {input} ein / {output} aus",
    ),
    "cost_unpriced": (
        "{count} request(s) not included: no price found.",
        "{count} petició(ns) no incloses: no s'ha trobat el preu.",
        "{count} Anfrage(n) nicht enthalten: kein Preis gefunden.",
    ),
    "your_total": ("Your total: **{cost}**", "El teu total: **{cost}**", "Ihre Summe: **{cost}**"),
    "your_total_note": (
        "All conversations in *My history*.",
        "Totes les converses d'*El meu historial*.",
        "Alle Unterhaltungen in *Mein Verlauf*.",
    ),
    # --- Assistant page: references ---
    "page_number": ("page {page}", "pàgina {page}", "Seite {page}"),
    "found_by": ("{category} · found by {how}", "{category} · trobat per {how}", "{category} · gefunden über {how}"),
    "found_by_meaning": ("meaning (rank {rank}{value})", "significat (posició {rank}{value})", "Bedeutung (Rang {rank}{value})"),
    "found_by_keywords": (
        "keywords (rank {rank}{value})",
        "paraules clau (posició {rank}{value})",
        "Stichwörter (Rang {rank}{value})",
    ),
    "similarity_value": (", similarity {value}", ", similitud {value}", ", Ähnlichkeit {value}"),
    "score_value": (", score {value}", ", puntuació {value}", ", Punktzahl {value}"),
    "and": (" and ", " i ", " und "),
    "passages_found_for_answer": (
        "Passages found for this answer: {numbers}. See the References tab.",
        "Fragments trobats per a aquesta resposta: {numbers}. Mira la pestanya Referències.",
        "Für diese Antwort gefundene Passagen: {numbers}. Siehe Reiter Quellen.",
    ),
    # --- Assistant page: chat ---
    "steps": ("Steps", "Passos", "Schritte"),
    "step_write": ("Write work product", "Escriure el document de treball", "Arbeitsergebnis schreiben"),
    "step_reread": ("Re-read passages", "Rellegir fragments", "Passagen erneut lesen"),
    "step_search": ("Search", "Cerca", "Suche"),
    "step_found": ("Found", "Trobat", "Gefunden"),
    "error_api_key": (
        "The API key {name} was not found. Set it as an environment variable, or copy .env.example "
        "to .env and fill it in, then restart the app.",
        "No s'ha trobat la clau d'API {name}. Defineix-la com a variable d'entorn, o copia "
        ".env.example a .env i omple-la; després reinicia l'aplicació.",
        "Der API-Schlüssel {name} wurde nicht gefunden. Setzen Sie ihn als Umgebungsvariable oder "
        "kopieren Sie .env.example nach .env und tragen Sie ihn ein; starten Sie dann die App neu.",
    ),
    "error_answer": (
        "Sorry, the answer could not be generated: {error}",
        "No s'ha pogut generar la resposta: {error}",
        "Die Antwort konnte leider nicht erstellt werden: {error}",
    ),
    "no_answer": (
        "I could not produce an answer. Please try rephrasing the question.",
        "No he pogut generar cap resposta. Prova de reformular la pregunta.",
        "Ich konnte keine Antwort erstellen. Bitte formulieren Sie die Frage um.",
    ),
    "guard_blocked": (
        "Your message was not passed on to the assistant: {reason} Please rephrase it.",
        "El teu missatge no s'ha passat a l'assistent: {reason} Reformula'l, si us plau.",
        "Ihre Nachricht wurde nicht an den Assistenten weitergegeben: {reason} Bitte formulieren Sie sie um.",
    ),
    "guard_no_verdict": (
        "The safety check could not judge your message. Please rephrase it.",
        "El control de seguretat no ha pogut valorar el teu missatge. Reformula'l, si us plau.",
        "Die Sicherheitsprüfung konnte Ihre Nachricht nicht beurteilen. Bitte formulieren Sie sie um.",
    ),
    "answer_interrupted": (
        "The last answer was interrupted (the page was left or reloaded while it ran). Please ask again.",
        "L'última resposta s'ha interromput (s'ha sortit de la pàgina o s'ha recarregat mentre es generava). "
        "Torna a preguntar, si us plau.",
        "Die letzte Antwort wurde unterbrochen (die Seite wurde währenddessen verlassen oder neu geladen). "
        "Bitte fragen Sie erneut.",
    ),
    "chat": ("Chat", "Xat", "Chat"),
    "new_conversation": ("New conversation", "Nova conversa", "Neue Unterhaltung"),
    "new_conversation_help": (
        "Clears the chat, the project input and the output. If you are logged in, the current "
        "conversation stays in My history.",
        "Esborra el xat, les dades del projecte i el resultat. Si has iniciat la sessió, la conversa "
        "actual es queda a El meu historial.",
        "Leert den Chat, die Projektangaben und das Ergebnis. Wenn Sie angemeldet sind, bleibt die "
        "aktuelle Unterhaltung in Mein Verlauf.",
    ),
    "export": ("Export", "Exporta", "Exportieren"),
    "export_help": (
        "Download this conversation: questions, answers, references and work product.",
        "Baixa aquesta conversa: preguntes, respostes, referències i document de treball.",
        "Diese Unterhaltung herunterladen: Fragen, Antworten, Quellen und Arbeitsergebnis.",
    ),
    "export_markdown": (
        "Markdown: to read, or to paste into a document.",
        "Markdown: per llegir-la o enganxar-la en un document.",
        "Markdown: zum Lesen oder zum Einfügen in ein Dokument.",
    ),
    "export_csv": (
        "CSV: one row per message, for Excel.",
        "CSV: una fila per missatge, per a l'Excel.",
        "CSV: eine Zeile pro Nachricht, für Excel.",
    ),
    "export_json": (
        "JSON: everything, including the search steps and costs.",
        "JSON: tot, també els passos de cerca i els costos.",
        "JSON: alles, auch die Suchschritte und Kosten.",
    ),
    "knowledge_base_empty": (
        "The knowledge base is empty. Open **Knowledge base** at the top to add documents.",
        "La base de coneixement és buida. Obre **Base de coneixement** a dalt per afegir-hi documents.",
        "Die Wissensbasis ist leer. Öffnen Sie oben **Wissensbasis**, um Dokumente hinzuzufügen.",
    ),
    "all_switched_off": (
        "All document types are switched off, so nothing can be searched.",
        "Tots els tipus de document estan desactivats, així que no es pot cercar res.",
        "Alle Dokumenttypen sind ausgeschaltet, daher kann nichts durchsucht werden.",
    ),
    "welcome": (
        "**Welcome!** I find the building rules that apply to your project in: {categories}. "
        "Every rule comes with its reference.",
        "**Benvingut/da!** Busco les normes d'edificació que s'apliquen al teu projecte a: {categories}. "
        "Cada norma té la seva referència.",
        "**Willkommen!** Ich finde die Bauvorschriften, die für Ihr Projekt gelten, in: {categories}. "
        "Jede Vorschrift mit ihrer Quelle.",
    ),
    "ask_intro": (
        "Click an example to ask it, or type your own question below:",
        "Fes clic en un exemple per preguntar-lo, o escriu la teva pregunta a sota:",
        "Klicken Sie auf ein Beispiel, um es zu fragen, oder schreiben Sie unten Ihre eigene Frage:",
    ),
    "example_1": (
        "Which rules apply to the project described in my files?",
        "Quines normes s'apliquen al projecte descrit als meus fitxers?",
        "Welche Vorschriften gelten für das in meinen Dateien beschriebene Projekt?",
    ),
    "example_2": (
        "Write a checklist of the fire-safety requirements for this project.",
        "Escriu una llista de comprovació dels requisits de seguretat en cas d'incendi d'aquest projecte.",
        "Schreiben Sie eine Checkliste der Brandschutzanforderungen für dieses Projekt.",
    ),
    "example_3": (
        "Where does the minimum distance to the plot boundary come from?",
        "D'on surt la distància mínima al límit de la parcel·la?",
        "Woher stammt der Mindestabstand zur Grundstücksgrenze?",
    ),
    "chat_placeholder": (
        "Ask about the rules for your project",
        "Pregunta per les normes del teu projecte",
        "Fragen Sie nach den Vorschriften für Ihr Projekt",
    ),
    "question_empty": ("Please type a question.", "Escriu una pregunta, si us plau.", "Bitte geben Sie eine Frage ein."),
    "question_too_long": (
        "The question is too long ({length} characters, maximum {max}).",
        "La pregunta és massa llarga ({length} caràcters, màxim {max}).",
        "Die Frage ist zu lang ({length} Zeichen, höchstens {max}).",
    ),
    "spending_limit_reached": (
        "The spending limit of {limit} per user is reached, so no more questions can be answered. "
        "Please contact the app owner.",
        "S'ha arribat al límit de despesa de {limit} per usuari, així que no es poden respondre més "
        "preguntes. Contacta amb el responsable de l'aplicació.",
        "Das Ausgabenlimit von {limit} pro Benutzer ist erreicht, daher können keine weiteren Fragen "
        "beantwortet werden. Bitte wenden Sie sich an den Betreiber der App.",
    ),
    # --- Assistant page: output ---
    "output": ("Output", "Resultat", "Ergebnis"),
    "work_product": ("Work product", "Document de treball", "Arbeitsergebnis"),
    "references": ("References", "Referències", "Quellen"),
    "search_steps": ("Search steps", "Passos de cerca", "Suchschritte"),
    "cited": ("cited", "citat", "zitiert"),
    "meaning": ("meaning", "significat", "Bedeutung"),
    "keywords": ("keywords", "paraules clau", "Stichwörter"),
    "on": ("on", "activada", "ein"),
    "off": ("off", "desactivada", "aus"),
    "settings_hybrid": ("hybrid search {state}", "cerca híbrida {state}", "hybride Suche {state}"),
    "settings_top_k": ("{count} passages per search", "{count} fragments per cerca", "{count} Passagen pro Suche"),
    "settings_searches": ("up to {count} searches", "fins a {count} cerques", "bis zu {count} Suchen"),
    "settings_switched_off": ("switched off: {names}", "desactivats: {names}", "ausgeschaltet: {names}"),
    "settings_all_on": ("all document types on", "tots els tipus de document activats", "alle Dokumenttypen eingeschaltet"),
    "settings": ("Settings", "Configuració", "Einstellungen"),
    "question": ("Question", "Pregunta", "Frage"),
    "answer": ("Answer", "Resposta", "Antwort"),
    "search_n": ("Search {number}", "Cerca {number}", "Suche {number}"),
    "reread": ("Re-read", "Relectura", "Erneut gelesen"),
    "write": ("Write", "Escriptura", "Schreiben"),
    "reread_note": ("found earlier, no new search", "trobats abans, sense cerca nova", "früher gefunden, keine neue Suche"),
    "answer_cites": (
        "cites {cited} of the {found} passages found. The passage texts are in the References tab.",
        "cita {cited} dels {found} fragments trobats. Els textos són a la pestanya Referències.",
        "zitiert {cited} der {found} gefundenen Passagen. Die Texte stehen im Reiter Quellen.",
    ),
    "answer_without_search": (
        "written without searching the knowledge base.",
        "escrita sense cercar a la base de coneixement.",
        "ohne Suche in der Wissensbasis geschrieben.",
    ),
    "steps_empty": (
        "After each answer you see here what the assistant did: every search it made, the passages "
        "it was given for it, and how well each passage matched.",
        "Després de cada resposta veuràs aquí què ha fet l'assistent: cada cerca, els fragments que "
        "ha rebut i com de bé coincidia cada fragment.",
        "Nach jeder Antwort sehen Sie hier, was der Assistent getan hat: jede Suche, die Passagen, "
        "die er dafür erhalten hat, und wie gut jede Passage gepasst hat.",
    ),
    "document_empty": (
        "Nothing here yet. Ask in the chat for a document, for example a checklist or a list of the "
        "rules that apply to your project. It appears here, and you can ask for changes.",
        "Encara no hi ha res. Demana un document al xat, per exemple una llista de comprovació o la "
        "llista de normes que s'apliquen al teu projecte. Apareixerà aquí i hi podràs demanar canvis.",
        "Noch nichts da. Bitten Sie im Chat um ein Dokument, zum Beispiel eine Checkliste oder eine "
        "Liste der Vorschriften für Ihr Projekt. Es erscheint hier, und Sie können Änderungen verlangen.",
    ),
    "download": ("Download", "Baixa", "Herunterladen"),
    "references_empty": (
        "Every passage the assistant finds in this conversation is listed here, with its document and page.",
        "Aquí es llisten tots els fragments que l'assistent troba en aquesta conversa, amb el document i la pàgina.",
        "Hier steht jede Passage, die der Assistent in dieser Unterhaltung findet, mit Dokument und Seite.",
    ),
    # --- Exported conversation (export.py) ---
    "conversation": ("Conversation", "Conversa", "Unterhaltung"),
    "exported_on": ("Exported on {date}", "Exportada el {date}", "Exportiert am {date}"),
    "you": ("You", "Tu", "Sie"),
    "assistant": ("Assistant", "Assistent", "Assistent"),
    # --- Flow diagram (flow_diagram.py) ---
    "stage_guard": ("Checking the question…", "Revisant la pregunta…", "Frage wird geprüft…"),
    "stage_model": ("Thinking…", "Pensant…", "Denkt nach…"),
    "stage_search": ("Reading the knowledge base…", "Llegint la base de coneixement…", "Wissensbasis wird gelesen…"),
    "stage_write": ("Writing the work product…", "Escrivint el document de treball…", "Arbeitsergebnis wird geschrieben…"),
    "stage_answer": ("Answering…", "Responent…", "Antwortet…"),
    "node_you": ("You", "Tu", "Sie"),
    "node_you_sub": ("question", "pregunta", "Frage"),
    "node_guard": ("Guard", "Filtre", "Wächter"),
    "node_guard_sub": ("safety check", "seguretat", "Sicherheit"),
    "node_model": ("Model", "Model", "Modell"),
    "node_model_sub": ("LLM", "LLM", "LLM"),
    "node_search": ("Knowledge base", "Base de coneixement", "Wissensbasis"),
    "node_search_sub": ("RAG search", "cerca RAG", "RAG-Suche"),
    "node_write": ("Work product", "Document", "Arbeitsergebnis"),
    "node_write_sub": ("tool", "eina", "Werkzeug"),
    "node_answer": ("Answer", "Resposta", "Antwort"),
    "node_answer_sub": ("chat", "xat", "Chat"),
    # --- Knowledge base page (page_library.py) ---
    "library_caption": (
        "The documents the assistant can search. Each document belongs to one category.",
        "Els documents en què l'assistent pot cercar. Cada document pertany a una categoria.",
        "Die Dokumente, die der Assistent durchsuchen kann. Jedes Dokument gehört zu einer Kategorie.",
    ),
    "admin_only": (
        "Only the admin can add or remove documents.",
        "Només l'administrador pot afegir o treure documents.",
        "Nur der Administrator kann Dokumente hinzufügen oder entfernen.",
    ),
    "changes_temporary": (
        "Changes made on this page are temporary: on the hosted app they are lost at the next "
        "restart. Permanent changes: add or remove files in data/library/ locally, run "
        "build_index.bat, then commit and push.",
        "Els canvis fets en aquesta pàgina són temporals: a l'aplicació allotjada es perden en el "
        "següent reinici. Canvis permanents: afegeix o treu fitxers a data/library/ en local, executa "
        "build_index.bat i després fes commit i push.",
        "Änderungen auf dieser Seite sind vorübergehend: In der gehosteten App gehen sie beim nächsten "
        "Neustart verloren. Dauerhafte Änderungen: Dateien lokal in data/library/ hinzufügen oder "
        "entfernen, build_index.bat ausführen, dann committen und pushen.",
    ),
    "add_documents": ("Add documents", "Afegeix documents", "Dokumente hinzufügen"),
    "category": ("Category", "Categoria", "Kategorie"),
    "files_allowed": (
        "Files ({types}, up to {mb} MB each)",
        "Fitxers ({types}, fins a {mb} MB cadascun)",
        "Dateien ({types}, je bis zu {mb} MB)",
    ),
    "add_to_library": ("Add to knowledge base", "Afegeix a la base de coneixement", "Zur Wissensbasis hinzufügen"),
    "choose_file": ("Choose at least one file first.", "Tria primer almenys un fitxer.", "Wählen Sie zuerst mindestens eine Datei."),
    "indexing": (
        "Indexing {count} file(s) into “{category}”…",
        "Indexant {count} fitxer(s) a «{category}»…",
        "{count} Datei(en) werden in „{category}“ indexiert…",
    ),
    "reading_file": (
        "Reading, splitting and embedding **{name}**…",
        "Llegint, dividint i vectoritzant **{name}**…",
        "**{name}** wird gelesen, aufgeteilt und eingebettet…",
    ),
    "chunks_indexed": ("{name}: {count} chunks indexed.", "{name}: {count} fragments indexats.", "{name}: {count} Abschnitte indexiert."),
    "tokens_cost": ("{tokens} tokens · {cost}", "{tokens} tokens · {cost}", "{tokens} Tokens · {cost}"),
    "embedding_cost": ("Embedding: {cost}", "Embeddings: {cost}", "Embedding: {cost}"),
    "finished_with_problems": (
        "Finished with {count} problem(s). {cost}",
        "Acabat amb {count} problema(es). {cost}",
        "Mit {count} Problem(en) beendet. {cost}",
    ),
    "files_added": (
        "{count} file(s) added to “{category}”. {cost}",
        "{count} fitxer(s) afegit(s) a «{category}». {cost}",
        "{count} Datei(en) zu „{category}“ hinzugefügt. {cost}",
    ),
    "documents_count": ("Documents ({count})", "Documents ({count})", "Dokumente ({count})"),
    "document_details": (
        "{chunks} chunks · {sections} sections · added {date}",
        "{chunks} fragments · {sections} seccions · afegit el {date}",
        "{chunks} Abschnitte · {sections} Gliederungspunkte · hinzugefügt am {date}",
    ),
    "remove_document": (
        "Remove this document from the knowledge base",
        "Treu aquest document de la base de coneixement",
        "Dieses Dokument aus der Wissensbasis entfernen",
    ),
    "maintenance": ("Maintenance", "Manteniment", "Wartung"),
    "maintenance_caption": (
        "Rebuild the search index from the files in data/library/. Needed after changing the chunk "
        "size, the heading rules or the embedding model. Every document is embedded again, which "
        "costs API credits. To only add files that were copied into the folders, or drop deleted "
        "ones, run build_index.bat instead.",
        "Reconstrueix l'índex de cerca a partir dels fitxers de data/library/. Cal fer-ho després de "
        "canviar la mida dels fragments, les regles dels títols o el model d'embeddings. Tots els "
        "documents es tornen a vectoritzar, cosa que consumeix crèdit de l'API. Per afegir només els "
        "fitxers copiats a les carpetes, o treure els esborrats, executa build_index.bat.",
        "Den Suchindex aus den Dateien in data/library/ neu aufbauen. Nötig nach einer Änderung der "
        "Abschnittsgröße, der Überschriftenregeln oder des Embedding-Modells. Jedes Dokument wird neu "
        "eingebettet, was API-Guthaben kostet. Um nur in die Ordner kopierte Dateien hinzuzufügen "
        "oder gelöschte zu entfernen, führen Sie stattdessen build_index.bat aus.",
    ),
    "rebuild_index": ("Rebuild index", "Reconstrueix l'índex", "Index neu aufbauen"),
    "rebuild_warning": (
        "All {count} file(s) in data/library/ will be embedded again: about {tokens} tokens, about "
        "{cost}. The current index is deleted first.",
        "Es tornaran a vectoritzar els {count} fitxer(s) de data/library/: uns {tokens} tokens, "
        "uns {cost}. Primer s'esborra l'índex actual.",
        "Alle {count} Datei(en) in data/library/ werden neu eingebettet: etwa {tokens} Tokens, etwa "
        "{cost}. Der aktuelle Index wird zuerst gelöscht.",
    ),
    "yes_rebuild": ("Yes, rebuild", "Sí, reconstrueix", "Ja, neu aufbauen"),
    "cancel": ("Cancel", "Cancel·la", "Abbrechen"),
    "rebuilding": ("Rebuilding the index…", "Reconstruint l'índex…", "Index wird neu aufgebaut…"),
    "rebuilt": (
        "{count} document(s) indexed. Embedding: {cost}",
        "{count} document(s) indexat(s). Embeddings: {cost}",
        "{count} Dokument(e) indexiert. Embedding: {cost}",
    ),
    "app_settings": ("App settings", "Configuració de l'aplicació", "App-Einstellungen"),
    "app_settings_caption": (
        "Saved for everyone. Users can still change the search settings for their own conversation; "
        "new conversations start with these.",
        "Es desa per a tothom. Cada usuari pot canviar la configuració de cerca de la seva conversa; "
        "les converses noves comencen amb aquesta.",
        "Für alle gespeichert. Benutzer können die Sucheinstellungen ihrer eigenen Unterhaltung "
        "weiterhin ändern; neue Unterhaltungen beginnen mit diesen.",
    ),
    "defaults_heading": (
        "**Defaults for new conversations**",
        "**Valors inicials de les converses noves**",
        "**Standardwerte für neue Unterhaltungen**",
    ),
    "types_switched_on": ("Document types switched on", "Tipus de document activats", "Eingeschaltete Dokumenttypen"),
    "passages_per_search": ("Passages per search", "Fragments per cerca", "Passagen pro Suche"),
    "searches_per_answer": ("Searches per answer", "Cerques per resposta", "Suchen pro Antwort"),
    "app_rules": ("**App rules**", "**Normes de l'aplicació**", "**App-Regeln**"),
    "spending_limit": (
        "Spending limit per user (USD)",
        "Límit de despesa per usuari (USD)",
        "Ausgabenlimit pro Benutzer (USD)",
    ),
    "spending_limit_help": (
        "Logged in: over all conversations of the user. Not logged in: per browser session.",
        "Amb sessió iniciada: sobre totes les converses de l'usuari. Sense sessió: per sessió del navegador.",
        "Angemeldet: über alle Unterhaltungen des Benutzers. Nicht angemeldet: pro Browsersitzung.",
    ),
    "guard_setting": (
        "Safety check of every question (guard)",
        "Control de seguretat de cada pregunta (filtre)",
        "Sicherheitsprüfung jeder Frage (Wächter)",
    ),
    "guard_setting_help": (
        "Off: questions go to the chat model unchecked. Only for testing.",
        "Desactivat: les preguntes arriben al model sense revisar. Només per a proves.",
        "Aus: Fragen gehen ungeprüft an das Chatmodell. Nur zum Testen.",
    ),
    "save_for_everyone": ("Save for everyone", "Desa per a tothom", "Für alle speichern"),
    "reset_defaults": ("Reset to code defaults", "Restableix els valors del codi", "Auf Code-Standardwerte zurücksetzen"),
    "reset_defaults_help": (
        "Forget the saved app settings and use the values of settings.py again.",
        "Oblida la configuració desada i torna a fer servir els valors de settings.py.",
        "Die gespeicherten App-Einstellungen verwerfen und wieder die Werte aus settings.py verwenden.",
    ),
    "reset_done": (
        "App settings reset to the code defaults.",
        "S'ha restablert la configuració als valors del codi.",
        "App-Einstellungen auf die Code-Standardwerte zurückgesetzt.",
    ),
    "reset_backup_failed": (
        "Reset on this server, but the backup to GitHub failed: {error}",
        "Restablert en aquest servidor, però la còpia a GitHub ha fallat: {error}",
        "Auf diesem Server zurückgesetzt, aber die Sicherung auf GitHub ist fehlgeschlagen: {error}",
    ),
    "settings_saved": ("App settings saved.", "S'ha desat la configuració.", "App-Einstellungen gespeichert."),
    "saved_backup_failed": (
        "Saved on this server, but the backup to GitHub failed: {error}",
        "Desat en aquest servidor, però la còpia a GitHub ha fallat: {error}",
        "Auf diesem Server gespeichert, aber die Sicherung auf GitHub ist fehlgeschlagen: {error}",
    ),
    # --- My history page (page_history.py) ---
    "history_login_needed": (
        "Log in or create an account (in the sidebar) to save your conversations and work products here.",
        "Inicia la sessió o crea un compte (a la barra lateral) per desar aquí les teves converses i documents.",
        "Melden Sie sich an oder erstellen Sie ein Konto (in der Seitenleiste), um Ihre Unterhaltungen "
        "und Arbeitsergebnisse hier zu speichern.",
    ),
    "history_empty": (
        "No saved conversations yet. Every conversation you have on the Assistant page is saved here.",
        "Encara no hi ha converses desades. Cada conversa que tinguis a la pàgina Assistent es desa aquí.",
        "Noch keine gespeicherten Unterhaltungen. Jede Unterhaltung auf der Seite Assistent wird hier gespeichert.",
    ),
    "history_summary": (
        "{count} conversation(s) of **{user}**, last changed first · total spent: **{cost}**",
        "{count} conversa(es) de **{user}**, la darrera modificada primer · total gastat: **{cost}**",
        "{count} Unterhaltung(en) von **{user}**, zuletzt geänderte zuerst · insgesamt ausgegeben: **{cost}**",
    ),
    "n_messages": ("{count} messages", "{count} missatges", "{count} Nachrichten"),
    "no_model_requests": ("no model requests", "cap petició al model", "keine Modellanfragen"),
    "open": ("Open", "Obre", "Öffnen"),
}


def text(key: str, language: str, **values) -> str:
    """The text `key` in `language` (a code of LANGUAGES), with the {placeholders} filled in from `values`.

    An unknown language falls back to the default language.

    Raises:
        KeyError: `key` is not in TEXTS (a typo in the code), or a placeholder has no value.
    """
    index = LANGUAGES.index(language) if language in LANGUAGES else LANGUAGES.index(DEFAULT_LANGUAGE)
    return TEXTS[key][index].format(**values)
