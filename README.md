# IssuerScope — online monitor voor officieel bedrijfsnieuws

**Dit is een installatiepakket, geen reeds gepubliceerd webadres.** Na eenmalige plaatsing in je eigen GitHub-account draait de monitor op GitHub en blijft hij werken wanneer je computer uit staat.

## Snel starten zonder programmeerkennis

1. Maak (als je dat nog niet hebt) een account op [github.com](https://github.com/).
2. Maak via **https://github.com/new** een **public** repository met de naam `bedrijfsnieuws-monitor`. Zet de optie om automatisch een README te maken **uit**, zodat de repository leeg begint.
3. Pak het ZIP-bestand van dit project uit. Open de uitgepakte projectmap. Zet indien nodig verborgen bestanden aan (op Mac `Cmd`+`Shift`+`.`), zodat de map `.github` ook zichtbaar is.
4. Kies in de lege GitHub-repository **uploading an existing file** of **Add file > Upload files**. Sleep **alle bestanden en mappen binnen de uitgepakte projectmap** naar het GitHub-venster, dus óók de map `.github`. Gebruik bij voorkeur Chrome of Edge wanneer een browser een map niet goed herkent. Kies **Commit directly to the main branch** en bevestig met **Commit changes**.
5. Controleer of je bovenaan in GitHub de map `.github` en het bestand `bedrijven.csv` ziet. Open `.github/workflows/dagelijkse_monitor.yml` om te controleren dat de workflow ook goed is aangekomen.
6. Ga naar **Settings > Pages** van je GitHub-repository. Kies bij **Build and deployment / Source**: **GitHub Actions**.
7. Ga naar **Actions**, open **Dagelijkse bedrijfsmonitor**, kies **Run workflow**, laat `verversen` geselecteerd en klik op de groene **Run workflow**.
8. Nadat de actie succesvol is uitgevoerd, vind je de URL van het dashboard onder **Settings > Pages**. Die ziet er bij een projectrepository normaal uit als `https://JOUW_GITHUB_NAAM.github.io/bedrijfsnieuws-monitor/`. Bewaar de URL als favoriet. Je hoeft de laptop hierna niet aan te laten.

Het precieze webadres ontstaat pas in jouw GitHub-account. Het is nog niet door de maker online gezet.

## Dagelijks gebruiken

- Open het Pages-webadres in de browser op laptop, tablet of telefoon.
- Onder **Nieuws & publicaties** zie je wat is binnengekomen, met filters op bedrijf, datum, categorie en gelezen/ongelezen.
- Klik op een titel voor de oorspronkelijke publicatie op de officiële bedrijfssite.
- Onder **Broncontrole** zie je bronnen met problemen. **Geen berichten gevonden is niet hetzelfde als geen bedrijfsnieuws.**
- Met **Exporteer nieuws als CSV** kun je de zichtbare selectie openen in Excel.
- De knop **Gelezen** bewaart zijn status alleen in dezelfde browser, niet in de cloud.

### Automatisch tijdstip

De workflow is ingesteld op **elke dag om 07.23 uur Belgische tijd** (Europe/Brussels, zomer- en wintertijd). GitHub kan geplande runs vertragen of in uitzonderlijke gevallen overslaan. Controleer daarom de datum **Laatste controle** op het dashboard. In **public repositories** kan GitHub geplande workflows uitschakelen als er **60 dagen geen repository-activiteit** is; heractiveer die dan via **Actions**. Af en toe een handmatige run of bijwerken kan nuttig zijn.

## Bedrijf toevoegen: geen code schrijven

1. Open je repository op GitHub en kies **Actions > Dagelijkse bedrijfsmonitor > Run workflow**.
2. Kies bij **actie**: `toevoegen`.
3. Vul bij **bedrijf** de exacte bedrijfsnaam in en (indien gekend) de ticker.
4. Vul **website** in, bijvoorbeeld `https://www.apple.com`.
5. Vul **bronnaam** in, bijvoorbeeld `Investor relations`.
6. Vul **bronurl** in: de officiële RSS-feed of de officiële pagina met persberichten/resultaten. Kies bij **brontype** `rss`, `html` of `auto` (probeert eerst RSS te herkennen).
7. Klik **Run workflow**. De bron wordt toegevoegd, gecontroleerd en in het dashboard gepubliceerd. Om **meerdere nieuwsbronnen per bedrijf** te volgen, herhaal de handeling met dezelfde bedrijfsnaam en een andere bron-URL.

Let op: een bedrijfsnaam is niet genoeg. Een officiële bron-URL is nodig om te waarborgen dat het bericht echt van het bedrijf afkomstig is. Nieuwsfeeds zijn doorgaans betrouwbaarder dan HTML-pagina's, die kunnen veranderen of nieuws met JavaScript kunnen laden.

## Bedrijf verwijderen

1. Open **Actions > Dagelijkse bedrijfsmonitor > Run workflow**.
2. Kies bij **actie**: `verwijderen`.
3. Vul de **exacte bedrijfsnaam** in zoals opgenomen in `bedrijven.csv`.
4. Klik **Run workflow**. Alle bronnen van dat bedrijf verdwijnen uit de actieve lijst; oude artikelen blijven achter in het archief maar zijn niet meer zichtbaar.

## Een lijst van 100+ bedrijven bijwerken via Excel

- Download het bestand `bedrijven.csv` uit je GitHub-repository (of uit het ZIP-pakket) en open het in Excel. Het bestand gebruikt een **puntkomma** als scheidingsteken.
- Voeg één regel toe per **officiële nieuwsbron**. Twee verschillende bronnen voor één bedrijf betekenen twee regels met exact dezelfde bedrijfsnaam.
- Bewaar opnieuw als `CSV UTF-8 (door lijstscheidingstekens gescheiden)` of puntkomma-CSV.
- Vervang `bedrijven.csv` in je GitHub-repository via **Add file > Upload files** en bevestig het overschrijven van het bestaande bestand. Een wijziging aan de lijst start de controle automatisch, mits Actions is ingeschakeld.

| Kolom | Betekenis | Voorbeeld |
|---|---|---|
| `bedrijf` | Exacte naam, gelijk voor meerdere bronnen | Apple |
| `ticker` | Beurscode (optioneel) | AAPL |
| `officiele_website` | Officieel bedrijfsdomein (https) | https://www.apple.com |
| `bron_naam` | Aanduiding van bron | Apple Newsroom |
| `bron_url` | Volledige URL van RSS of perspagina | https://www.apple.com/newsroom/rss-feed.rss |
| `bron_type` | `rss`, `html` of `auto` | rss |
| `actief` | `ja` of `nee` | ja |
| `extra_officiele_domeinen` | Extra bevestigd officieel domein, optioneel (zonder https); bij meer dan één scheiden met `\|` |  |

**Stop tijdelijk** met het volgen van een bron door `actief` op `nee` te zetten. **Verwijder** de rij om de bron definitief uit de actieve controle te halen.

## Waaruit bestaat het pakket?

- `monitor.py`: automatische dagelijkse ophaler, kwaliteitscontrole en websitegenerator; werkt met standaard-Python, zonder betaalde API's.
- `dashboard_template.html`: vormgeving van de website.
- `.github/workflows/dagelijkse_monitor.yml`: de dagelijkse GitHub-taak en het beheerscherm.
- `bedrijven.csv`: makkelijk bewerkbare lijst met officiële bronnen.
- `data/`: blijvend nieuwsarchief en laatste broncontroles (wordt bij iedere run in GitHub opgeslagen).
- `site/index.html`: voorbeeld van het dashboard dat meteen lokaal kan worden geopend; GitHub maakt dit na de eerste run bij met actuele gegevens.

## Dekking en betrouwbaarheid

- Dit is een **functionele basis**, geen gegarandeerd volledige bedrijfsdisclosure-databank. De eerste lijst bevat twee voorbeeldbedrijven met rechtstreeks gepubliceerde RSS-bronnen. Om tientallen of meer dan 100 bedrijven te dekken, moet je hun *officiële* bronnen eenmalig toevoegen en verifiëren.
- De monitor leest alleen de opgegeven bronnen en volgt externe links of redirects niet. Een derde partij of nieuwsmedia worden niet geraadpleegd.
- Sommige bedrijven publiceren via investor-relations-platformen of pdf's op andere domeinen. Zet een **daadwerkelijk door het bedrijf gecontroleerd** extra domein expliciet in de lijst als dat nodig is.
- PDF-inhoud wordt **niet doorzocht**; een PDF wordt alleen gevonden als die rechtstreeks in de bronlijst zichtbaar is.
- Sommige websites werken uitsluitend via JavaScript, blokkeren geautomatiseerde verzoeken, of bieden geen leesbare feed. Dit verschijnt bij Broncontrole of kan tot gemiste artikelen leiden.
- Bij de eerste succesvolle controle van een bron worden aanwezige oude berichten als **Startarchief** gelabeld. Daarna zijn nieuw ontdekte berichten afzonderlijk herkenbaar.
- **Publicatiedatum** komt uit RSS/Atom. Als een webpagina die niet machineleesbaar meestuurt, tonen we **Niet vermeld**. **Ontdekt** is onze eigen controledatum.
- Indeling in Financieel/Operationeel/Bestuur/Overig werkt op trefwoorden en kan onjuist zijn.
- Het bewaart maximaal 20.000 berichten in het archief. Voor zeer groot gebruik of gegarandeerde volledigheid is een database en commerciële monitoringinfrastructuur beter geschikt.

## Privacy en beheer

Een GitHub Pages-site bij een public repository is **publiek toegankelijk**. Ook je bedrijvenlijst en gearchiveerde berichten in dat repository zijn openbaar. Plaats hier dus **geen vertrouwelijke interne informatie** in. Overleg met je IT-afdeling voor zakelijk gebruik. Als je een afgeschermde toepassing nodig hebt, kies dan een private cloud-implementatie met toegangsauthenticatie in plaats van deze gratis publieke versie.

## Storingen

- **Dashboard niet beschikbaar?** Kijk in **Settings > Pages** of de bron **GitHub Actions** is gekozen; controleer de laatste rode of groene actie onder **Actions**.
- **Bijwerken mislukt?** Ga naar de rode run onder **Actions** en open de stap **Verzamel alleen officiële bedrijfsberichten**. De foutmelding noemt vaak het probleem, bijvoorbeeld een ongeldig domein of CSV-kolom.
- **Geen nieuws?** Bekijk **Broncontrole**, controleer het officiële URL-adres en voeg waar mogelijk een RSS-feed toe.
- **Run blijft uit?** Controleer de laatste werkdatum, of Actions niet is uitgeschakeld, en start desnoods handmatig `verversen`.

GitHub-handleidingen: [Pages instellen](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) · [Geplande acties](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).
