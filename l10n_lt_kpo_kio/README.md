# 🇱🇹 Lietuvos KPO ir KIO orderiai (Odoo 19)

**Modulio pavadinimas:** `l10n_lt_kpo_kio`  
**Versija:** 19.0.31.0.0  
**Suderinamumas:** Odoo 19.0 (Enterprise / Community)  
**Kategorija:** Apskaita / Lokalizacija  

Tai oficialus lokalizacijos modulis, skirtas formuoti ir spausdinti Lietuvos Respublikos buhalterinius reikalavimus atitinkančius **Kasos Pajamų Orderius (KPO)** ir **Kasos Išlaidų Orderius (KIO)**. Modulis pritaikytas sklandžiam darbui tiek apskaitos (kasos žurnalo), tiek Pardavimo taško (POS) moduliuose.

## ✨ Pagrindinės funkcijos

1. **POS Integracija (Be OWL klaidų rizikos):**
   * Saugus KPO spausdinimo mygtukas įterptas į vidinį POS užsakymo formos langą (Backend), taip išvengiant jautraus Odoo 19 OWL variklio klaidų (angl. *White Screen of Death*), kurios dažnai pasitaiko modifikuojant kasos čekio (Receipt Screen) atvaizdavimą.
   * Mygtukas matomas tik tada, jei užsakymas apmokėtas naudojant KPO mokėjimo būdą ir funkcija įjungta POS nustatymuose.

2. **Banko išrašų / Kasos žurnalo integracija:**
   * Galimybė spausdinti KPO (gavus pinigus) ir KIO (išmokėjus pinigus) tiesiai iš Banko sąskaitos sudengimo (`account.bank.statement.line`) lango per „Veiksmai“ (Action) meniu.
   * Sistema automatiškai atpažįsta operacijos tipą: teigiama suma generuoja KPO, neigiama – KIO.

3. **Išmanusis PDF A4 Šablonas:**
   * Klasikinis, oficialus blanko dizainas (viršuje – orderis, apačioje – kvitas su kirpimo linija).
   * **Automatinė suma žodžiais:** Modulyje integruotas algoritmas, kuris sumą skaičiais automatiškai paverčia lietuvišku tekstu (pvz., *Dvidešimt aštuoni Eur, 00 ct.*).
   * **Skaitmeniniai parašai:** Automatinis kasininko (prisijungusio vartotojo) skaitmeninio parašo paėmimas iš Odoo `sign` modulio vartotojo profilio.

## ⚙️ Diegimas ir Konfigūracija

**Priklausomybės (Dependencies):** Modulis reikalauja, kad sistemoje būtų įdiegti šie standartiniai Odoo moduliai: `account`, `sign`, `point_of_sale`.

**Sąranka:**
1. **POS KPO įjungimas:** Eikite į *Pardavimo taškas -> Konfigūracija -> Nustatymai*. Raskite bloką „Lietuvos KPO Nustatymai“ ir pažymėkite varnelę **Spausdinti KPO (A4)**.
2. **Kasininko parašas:** Eikite į viršutinį dešinįjį kampą -> *Mano profilis*. Skiltyje „Parašas“ (Sign Signature) įkelkite savo parašo nuotrauką (rekomenduojama .PNG formatu be fono).

## 🚀 Naudojimo instrukcija

* **Pardavimo taške (POS):** Užbaigę pardavimą su KPO mokėjimo metodu, paspauskite mygtuką „Registruotas“ (Edit Payment). Atsidariusiame užsakymo lange, viršuje kairėje, rasite mėlyną mygtuką „Spausdinti KPO (A4)“.
* **Apskaitoje:** Eikite į *Apskaita -> Banko sąskaitos sudengimas*. Pažymėkite norimą kasos operacijos eilutę, paspauskite mygtuką „Veiksmai“ ⚙️ ir pasirinkite „Spausdinti KPO / KIO (A4)“.

## 🛠 Techninė informacija (Kūrėjams)
* Modulis nenaudoja jokio papildomo *JavaScript* ar *XML/OWL* kodo klientinėje dalyje (Frontend), taip užtikrinant 100% stabilumą atnaujinant Odoo versijas. Visa ataskaitų generavimo logika veikia *Python* / *QWeb* aplinkoje (Backend).
