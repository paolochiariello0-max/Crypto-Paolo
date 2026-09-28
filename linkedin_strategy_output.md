import os
from crewai import Agent, Crew, Process, Task

# ==============================================================================
# 1. INPUT DATO DALL'UTENTE (Personalizza questi dati)
# ==============================================================================
USER_PROFILE_DATA = """
- Nome: Marco Rossi
- Ruolo attuale: Senior AI Consultant / Fractional CTO
- Target di clienti: PMI e Startup B2B che vogliono integrare l'IA nei loro processi.
- Esperienze chiave: 8 anni nel software engineering, coordinate 15+ trasformazioni digitali, ex-Tech Lead in scaleup fintech.
- Risultati principali: Riduzione dei tempi di operatività del 40% per cliente X, gestione budget da 1M€.
- Obiettivo su LinkedIn: Aumentare l'autorità nel settore AI/B2B e generare lead di clienti qualificati per consulenze.
- Tono di voce desiderato: Pragmatico, autorevole, diretto, senza "fuffa" o frasi fatte da AI.
"""

# ==============================================================================
# 2. DEFINIZIONE DEGLI AGENTI (Lo Sciame)
# ==============================================================================

# AGENTE 1: Strategist & SEO Profile Optimizer
profile_optimizer = Agent(
    role="LinkedIn Profile & SEO Strategist",
    goal="Trasformare il profilo LinkedIn in una landing page ad alta conversione ottimizzata per la SEO.",
    backstory=(
        "Sei il principale esperto mondiale di personal branding su LinkedIn. "
        "Sai esattamente quali keyword posizionare per farti trovare da recruter e clienti target. "
        "Sai come strutturare Sommario, Sezione Info e Esperienze per massimizzare il tasso di conversione."
    ),
    verbose=True,
    allow_delegation=False,
)

# AGENTE 2: Content Creator & Copywriter Virale
content_creator = Agent(
    role="LinkedIn Top Voice & Copywriter",
    goal="Creare post e caroselli ad alto engagement, con hook magnetici e valore pratico.",
    backstory=(
        "Sei un copywriter virale con milioni di visualizzazioni su LinkedIn. "
        "Conosci a memoria l'algoritmo di LinkedIn, eviti la banalità e scrivi con hook che spingono "
        "a cliccare subito su 'mostra altro'. Usi i 4 pilastri: Autorità, Empatia, Educazione, Conversione."
    ),
    verbose=True,
    allow_delegation=False,
)

# AGENTE 3: Growth & Engagement Specialist
engagement_growth = Agent(
    role="LinkedIn Growth Hacker & Network Strategist",
    goal="Progettare la strategia di interazione (commenti, DM, networking) per far esplodere la portata del profilo.",
    backstory=(
        "Sei un Growth Hacker focalizzato sul B2B. Sai come convertire le visualizzazioni in connessioni "
        "e le connessioni in chiamate di vendita tramite strategie di 'Golden Hour' e messaggi privati ad alto valore."
    ),
    verbose=True,
    allow_delegation=False,
)

# AGENTE 4: Orchestratore & Quality Control Manager
quality_manager = Agent(
    role="Chief Brand Officer & Quality Controller",
    goal="Revisionare ed eliminare qualsiasi stereotipo da intelligenza artificiale, garantendo uno stile umano e d'impatto.",
    backstory=(
        "Sei il guardiano della qualità del brand. Il tuo compito è eliminare frasi stantie come 'In un mondo sempre più digitale...', "
        "sfoltire l'uso eccessivo di emoji e verificare che il tono di voce sia 100% autentico, affilato e orientato ai risultati."
    ),
    verbose=True,
    allow_delegation=True,
)

# ==============================================================================
# 3. DEFINIZIONE DEI TASKS (I compiti degli agenti)
# ==============================================================================

task_profile = Task(
    description=(
        f"Analizza i seguenti dati dell'utente:\n{USER_PROFILE_DATA}\n\n"
        "Crea l'ottimizzazione completa del profilo:\n"
        "1. Tre opzioni di **Headline / Sommario** (Massimo 220 caratteri ciascuna, formattate: Impatto + Target + Keyword).\n"
        "2. Una sezione **Info (About)** avvincente usando il framework Problem-Agitation-Solution-CTA.\n"
        "3. La riscrittura di 1 **Esperienza Principale** applicando la formula: [Azione] + [Contesto] + [Risultato misurabile].\n"
        "4. Una lista delle **Top 10 Competenze / Keyword SEO** da inserire nel profilo."
    ),
    expected_output="Documento Markdown con Headline, Sezione Info, Esperienza riscritta e Keywords SEO.",
    agent=profile_optimizer,
)

task_content = Task(
    description=(
        "Sulla base del profilo e degli obiettivi stabiliti:\n"
        "1. Crea un **Piano Editoriale Semanale** (5 giorni) basato su 4 pilastri (Educazione, Autorità, Empatia, Conversione).\n"
        "2. Scrivi il testo completo di **2 Post Pronti da Pubblicare**:\n"
        "   - Post 1: Un post ad alta autorità/caso studio (con Hook d'impatto e formato leggibile a righe brevi).\n"
        "   - Post 2: Lo script slide-per-slide per un **Carosello PDF** di 5-6 slide con consigli pratici.\n"
        "Assicurati che ogni post termini con una Call to Action (CTA) efficace."
    ),
    expected_output="Piano editoriale settimanale e 2 post completi (uno testuale + uno script carosello).",
    agent=content_creator,
)

task_engagement = Task(
    description=(
        "Progetta la strategia di crescita attiva:\n"
        "1. Fornisci un **Framework per i Commenti**: 3 template di commenti ad alto valore da lasciare sotto i post dei top player del settore.\n"
        "2. Prepara 2 script di **Messaggi Privati (DM)**:\n"
        "   - Script A: Per nuovi collegamenti accettati (soft networking).\n"
        "   - Script B: Per seguire chi ha interagito con un post (conversione lead)."
    ),
    expected_output="Guida con 3 strategie di commento e 2 script DM personalizzabili.",
    agent=engagement_growth,
)

task_orchestration = Task(
    description=(
        "Prendi l'output generato dagli agenti di Profilo, Contenuti ed Engagement.\n"
        "1. Effettua una revisione stilistica rigorosa: rimuovi frasi generiche, linguaggio da brochure e pattern tipici delle AI.\n"
        "2. Assembla tutto in una **Strategia LinkedIn Integrata Finale** ben formattata in Markdown, pronti all'uso immediato."
    ),
    expected_output="Report finale in Markdown raffinato, professionale e privo di difetti di stile AI.",
    agent=quality_manager,
)

# ==============================================================================
# 4. ESECUZIONE DELLO SCIAME (Crew)
# ==============================================================================

if __name__ == "__main__":
    print("🚀 Avvio dello Sciame di Agenti per LinkedIn...\n")

    linkedin_crew = Crew(
        agents=[profile_optimizer, content_creator, engagement_growth, quality_manager],
        tasks=[task_profile, task_content, task_engagement, task_orchestration],
        process=Process.sequential,  # Gli agenti lavorano in sequenza logica
        verbose=True,
    )

    result = linkedin_crew.kickoff()

    print("\n==================================================")
    print("🎯 STRATEGIA E CONTENUTI LINKEDIN COMPLETATI")
    print("==================================================\n")
    print(result)

    # Salva il risultato finale in un file Markdown
    with open("linkedin_strategy_output.md", "w", encoding="utf-8") as f:
        f.write(str(result))

    print("\n✅ Risultato salvato con successo nel file 'linkedin_strategy_output.md'!")
