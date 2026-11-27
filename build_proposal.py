#!/usr/bin/env python3
"""Build the NOUN-format project proposal for the Aabo AI study.

Format follows the NOUN research manual as described in the format guide the
user supplied (monoed.africa/blog/noun-project-proposal-format): A4, Times New
Roman 12 pt, double line spacing, 1 inch margins, justified body text with
indented paragraphs, bold headings, chapter title in capitals and centred,
working title of 23 words or fewer, APA references.

Every number and every characterisation of a cited study is taken from the
project itself (Chapter One for the framing, Chapter Two for the literature,
Chapter Four for the measured results, ch6.md for the reference list) so that
the proposal cannot contradict the report it accompanies.
"""
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

OUT = "/Users/amarachi/Downloads/Proposal_Aabo_AI_Amarachi_Stella_Awazie.docx"

TITLE = "AI-POWERED PHISHING DETECTION AND URL CLASSIFICATION TOOL"

doc = Document()

# ---------------------------------------------------------------- page setup
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)          # A4
for m in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
    setattr(sec, m, Inches(1))                                 # 1 inch all sides

normal = doc.styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(12)
rpr = normal.element.get_or_add_rPr()
rf = rpr.find(qn("w:rFonts"))
if rf is None:
    rf = OxmlElement("w:rFonts")
    rpr.append(rf)
for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
    rf.set(qn(a), "Times New Roman")
pf = normal.paragraph_format
pf.line_spacing_rule = WD_LINE_SPACING.DOUBLE
pf.space_before = Pt(0)
pf.space_after = Pt(0)
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY


def _run(p, text, bold=False, italic=False):
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    r.font.name = "Times New Roman"
    r.font.size = Pt(12)
    return r


def p(text=""):
    """Body paragraph: justified, first line indented 0.5 inch, double spaced."""
    par = doc.add_paragraph()
    par.paragraph_format.first_line_indent = Inches(0.5)
    _run(par, text)
    return par


def h(text):
    """Numbered section heading: bold, left aligned, not indented."""
    par = doc.add_paragraph()
    _run(par, text, bold=True)
    return par


def li(text):
    """Numbered or lettered list item: hanging indent, no first-line indent."""
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Inches(0.5)
    par.paragraph_format.first_line_indent = Inches(-0.25)
    _run(par, text)
    return par


def centre(text="", bold=False, italic=False, space_after=0):
    par = doc.add_paragraph()
    par.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(space_after)
    if text:
        _run(par, text, bold=bold, italic=italic)
    return par


def ref(text):
    """APA reference: hanging indent half an inch."""
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Inches(0.5)
    par.paragraph_format.first_line_indent = Inches(-0.5)
    par.paragraph_format.space_after = Pt(12)
    _run(par, text)
    return par


def page_break():
    doc.add_page_break()


# ------------------------------------------------------------ page numbering
sec.different_first_page_header_footer = True   # no folio on the title page
ftr = sec.footer.paragraphs[0]
ftr.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
_r = ftr.add_run()
for kind, extra in (("begin", None), ("instr", "PAGE"), ("end", None)):
    if kind == "instr":
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = extra
    else:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), kind)
    _r._r.append(el)

# ================================================================ TITLE PAGE
centre()
centre("AI-POWERED PHISHING DETECTION AND URL CLASSIFICATION TOOL", bold=True)
centre("(A PROJECT PROPOSAL)")
centre()
centre("BY")
centre()
centre("AMARACHI STELLA AWAZIE", bold=True)
centre("NOU241741241")
centre()
centre("B.Sc. COMPUTER SCIENCE")
centre("DEPARTMENT OF COMPUTER SCIENCE")
centre("NATIONAL OPEN UNIVERSITY OF NIGERIA")
centre("[STUDY CENTRE]")
centre()
centre("SUPERVISOR: DR ADEWALE RILWAN")
centre()
centre("NOVEMBER 2026")
page_break()

# ============================================================ 1. INTRODUCTION
h("1. Introduction and Background to the Study")
p("The growth of internet-based services has changed the way people in Nigeria carry out "
  "everyday transactions. Banking, shopping, bill payment, admission processing and "
  "communication with government agencies now take place largely online. Nigeria's digital "
  "payment infrastructure reflects this shift: the country processed approximately 47.88 "
  "billion electronic payment transactions in 2025, and the Nigeria Inter-Bank Settlement "
  "System reported that banks and other financial institutions lost \u20a625.85 billion to "
  "electronic payment fraud in the same year, with phishing, social engineering, SIM swap and "
  "account compromise identified as the dominant threat vectors (Ejalonibu, Obot and Nandi, "
  "2026). Aggregate losses fell by 51 per cent from the \u20a652.26 billion recorded in 2024, but "
  "the same report observes that fraudulent activity is becoming more targeted, more "
  "technologically enabled and increasingly driven by artificial intelligence. Convenience has "
  "expanded alongside exposure.")
p("Phishing is the most common entry point for these attacks. The Anti-Phishing Working Group "
  "(2025) describes phishing as a form of cyberattack in which criminal actors impersonate a "
  "trusted organisation or individual in order to deceive a user into disclosing credentials, "
  "payment card details or other sensitive information, or into visiting a malicious website. "
  "The group recorded 1,003,924 phishing attacks in the first quarter of 2025 alone, the "
  "highest quarterly figure since late 2023, and observed that the majority of these attacks "
  "depended on a fraudulent link. A phishing campaign is therefore not primarily a technical "
  "intrusion into a network; it is an attempt to persuade a person to follow a web address "
  "that appears credible but leads to infrastructure controlled by the attacker.")
p("The web address, or uniform resource locator (URL), is consequently the point at which most "
  "phishing attacks either succeed or fail. Attackers construct addresses that imitate the "
  "sites their targets already trust, using misleading subdomains, brand names embedded in "
  "paths, misspellings of popular domains, numeric host addresses in place of domain names, "
  "and valid security certificates on hostile sites. Because these artefacts can be produced "
  "in large quantities and discarded within hours, a user who must judge a link in the middle "
  "of a working day, on a mobile phone, with limited technical background, is asked to perform "
  "a task that trained analysts find difficult. Established defences have not kept pace. "
  "Blacklists act only on addresses already reported, whitelists are impractical on the open "
  "internet, and rule-based filters detect only the attack families their authors anticipated. "
  "Rashid, Doyle, Han and Seneviratne (2024) further show that supervised detectors trained on "
  "one dataset lose effectiveness when tested against URLs drawn from a different source, "
  "because phishing domains are short-lived and constantly regenerated. Each of these "
  "approaches depends on prior knowledge of the attack.")
p("Machine learning offers a different basis for detection. Instead of matching an address "
  "against a list, a supervised algorithm is trained on a large body of labelled examples and "
  "learns the statistical relationship between measurable characteristics of an address and "
  "its true class, which permits generalisation from known malicious URLs to addresses it has "
  "never encountered (Breiman, 2001; Vapnik, 1999). Two families of classifiers are "
  "particularly suitable for a detector that works on the URL string alone: logistic "
  "regression, whose coefficients can be inspected and explained, and random forest, which "
  "captures non-linear interactions between features such as address length, hostname depth "
  "and the presence of misleading tokens. This study develops and evaluates such a system. A "
  "web-based tool is designed in which a user submits a URL and receives a classification of "
  "phishing or legitimate \u2014 or, where the bundled reputation lists contradict the model, a "
  "third state of unverified \u2014 together with a confidence score and an indication of the "
  "characteristics that influenced the decision. The system is trained and tested on the "
  "PhiUSIIL phishing URL dataset (Prasad and Chandra, 2024), a publicly available collection "
  "of 235,795 labelled URLs, and two classifiers, random forest and logistic regression, are "
  "trained on identical preprocessed data and compared across accuracy, precision, recall, "
  "F1-score and confusion matrices. That comparison is not incidental to the study: it "
  "determines which algorithm is deployed, and it answers a question that the designer of a "
  "security tool must settle before recommending a model to ordinary users.")

# =============================================================== 2. PROBLEM
h("2. Statement of the Problem")
p("Phishing attacks in Nigeria increasingly arrive as links, and the users who receive them "
  "are expected to judge in seconds whether a web address is genuine. This expectation is "
  "unreasonable, because the techniques used to disguise a malicious URL \u2014 brand names placed "
  "in the wrong part of an address, character substitutions, deep subdomain chains, host "
  "addresses in place of domain names and valid certificates on hostile sites \u2014 are designed "
  "to defeat visual inspection. Consequently, users in Nigeria continue to disclose "
  "credentials and card details to pages that display the correct logo of a bank or a payment "
  "platform, and financial institutions continue to absorb the resulting losses.")
p("The systems currently available to those users do not close the gap. Community blacklists "
  "such as PhishTank and OpenPhish cannot block a URL that has not yet been reported, and a "
  "freshly registered phishing domain operates during exactly the window in which its first "
  "victims encounter it. Rule-based and signature filters miss deliberately obfuscated or "
  "previously unseen URL structures. Commercial email and browser protections are bundled "
  "with paid products, operate inside a vendor's cloud and return a verdict without "
  "explanation, so a user cannot learn why a link was judged unsafe and an institution cannot "
  "audit the decision. Academic detectors reported in the literature achieve high accuracy on "
  "the dataset on which they were trained but degrade on URLs from another source (Rashid et "
  "al., 2024), and few are delivered as usable tools that a non-technical user can operate. "
  "Three specific problems therefore remain unresolved. First, detection must work on newly "
  "created URLs rather than only on addresses already known to be malicious, which requires a "
  "model that classifies from the address's own structure instead of its reputation. Second, "
  "the evidence available at the moment of decision is often only the URL string, because the "
  "user has not yet visited the page and, in a safe design, should not have to; a detector "
  "must therefore function without retrieving page content. Third, users and institutions "
  "need to understand a verdict, not merely receive one, which makes interpretability a "
  "requirement rather than an enhancement.")
p("There is also a gap in reported performance. Studies report accuracies between roughly 94 "
  "and 99.9 per cent using different algorithms, datasets and feature sets, but these results "
  "are rarely compared under identical preprocessing and evaluation conditions, and the choice "
  "of algorithm for a deployed, lightweight, URL-only tool is therefore made without direct "
  "evidence. This study addresses that gap by training a random forest classifier and a "
  "logistic regression classifier on the same features, the same split and the same "
  "evaluation protocol, and by using the measured outcome to decide which model the "
  "application will serve.")

# ================================================= 3. PURPOSE AND OBJECTIVES
h("3. Purpose and Objectives of the Study")
p("The purpose of this study is to develop an AI-powered phishing detection and URL "
  "classification tool that uses supervised machine-learning techniques to distinguish "
  "phishing URLs from legitimate ones, and to determine which of two classification "
  "algorithms, random forest and logistic regression, performs better for deployment in "
  "assisting internet users to recognise phishing threats. Specifically, the study:")
li("1. examines existing phishing detection techniques and currently deployed phishing "
   "detection systems, in order to establish their limitations, particularly their inability "
   "to identify newly created phishing URLs;")
li("2. obtains and preprocesses the PhiUSIIL phishing URL dataset, and extracts lexical and "
   "structural features from the URL string in order to produce suitable data for training and "
   "evaluating machine-learning models;")
li("3. develops and trains two supervised machine-learning classification models, random "
   "forest and logistic regression, capable of analysing URL characteristics and "
   "distinguishing potentially malicious URLs from legitimate ones;")
li("4. designs and implements a user-friendly web-based application that allows a user to "
   "submit a URL, receive a classification result with a confidence score, and see the URL "
   "characteristics that informed the decision; and")
li("5. evaluates and compares the performance of both models using accuracy, precision, "
   "recall, F1-score and confusion matrices, and tests the functionality and response time of "
   "the developed application.")

# ======================================================= 4. RESEARCH QUESTIONS
h("4. Research Questions")
p("The study is guided by the following research questions:")
li("1. What limitations do existing phishing detection techniques and deployed systems have "
   "in identifying newly created phishing URLs?")
li("2. Which URL-derived lexical and structural features can distinguish phishing URLs from "
   "legitimate ones?")
li("3. How accurately can random forest and logistic regression classify phishing URLs on the "
   "basis of those features?")
li("4. Which of the two algorithms performs better across accuracy, precision, recall and "
   "F1-score, and is therefore more suitable for deployment?")
li("5. How usable and responsive is the developed application for a non-technical internet "
   "user?")
p("The second and fourth questions compare measured performance rather than estimate a "
  "population parameter, and the comparison is therefore reported as a difference in measured "
  "accuracy, precision, recall and F1-score on identical data under an identical protocol. No "
  "inferential test of statistical significance is performed, and that omission is stated as "
  "a limitation of the study in the full report rather than presented as a statistical "
  "result.")

# ======================================================== 5. SIGNIFICANCE
h("5. Significance of the Study")
p("The findings of this study are significant to several groups.")
p("For individual internet users, particularly bank customers, students and small business "
  "owners who transact online in Nigeria, the tool provides a second opinion before a link is "
  "opened, and because the verdict is returned with the characteristics that produced it, the "
  "user is not only protected in that moment but gradually learns what a deceptive address "
  "looks like.")
p("For financial institutions and payment service providers, whose fraud losses reached "
  "\u20a625.85 billion in 2025 (Ejalonibu, Obot and Nandi, 2026), an open, URL-only classifier "
  "offers a low-cost pre-filtering layer that can be applied to links received through "
  "customer-facing channels, and a transparent verdict that supports dispute investigation, "
  "since the reasons behind a classification remain visible rather than being buried inside a "
  "vendor's black box.")
p("For regulators and law-enforcement agencies concerned with cybercrime, including the "
  "Central Bank of Nigeria, the Nigeria Inter-Bank Settlement System and the Economic and "
  "Financial Crimes Commission, the study contributes evidence on which algorithm family is "
  "appropriate for lightweight, deployable phishing detection in resource-constrained "
  "environments, and demonstrates a methodology that can be extended to local threat feeds.")
p("For the academic community, and particularly for students of Computer Science at the "
  "National Open University of Nigeria, the work contributes a controlled comparison of two "
  "supervised classifiers on identical data and identical features, a reproducible "
  "experimental procedure, and a documented example of the progression from literature review "
  "through model design to a functioning artefact.")
p("For software developers, the study documents the practical constraints of deploying a "
  "machine-learning model behind a web interface, including feature extraction at request "
  "time, model serialisation, response-time budgets and the presentation of probabilistic "
  "output to a non-technical audience.")

# ============================================================= 6. SCOPE
h("6. Scope of the Study")
p("Content scope. The system classifies a single URL string submitted by a user. Its features "
  "are lexical and structural properties computed from that string: length-based measures, "
  "hostname and path characteristics, the presence of an IP address or an at-symbol in the "
  "authority component, digit and special-character counts, subdomain depth, transport "
  "security, and the presence of tokens commonly associated with credential harvesting. These "
  "features require no network request beyond the submission itself, so classification is "
  "fast and safe. The system does not retrieve, render or analyse the content of the "
  "destination page, does not inspect email bodies or message headers, does not execute "
  "JavaScript and does not maintain a live reputation feed. It is not a browser extension and "
  "does not attempt to replace endpoint protection or an organisation's security stack. It "
  "classifies one URL at a time, and it does not attempt to identify the actor behind an "
  "attack or to attribute a campaign. Two supervised algorithms are compared, random forest "
  "and logistic regression, and no other model families are evaluated. Training and evaluation "
  "use the PhiUSIIL dataset and its URL and label columns only, excluding the dataset's "
  "content-derived features so that the training conditions match the conditions under which "
  "the deployed tool operates.")
p("Geographical scope. The system is developed, evaluated and deployed in Lagos, Nigeria, and "
  "it is intended for Nigerian internet users, for whom a curated local allow-list was "
  "assembled because no Nigerian domain appears within the first 100,000 ranks of the global "
  "popularity list that the reputation layer consults. The dataset itself is international, "
  "and the study does not claim that performance measured on any dataset establishes "
  "performance on live Nigerian traffic.")

# ===================================================== 7. LITERATURE REVIEW
h("7. Brief Review of Literature")
p("Conceptual review. Phishing is a deceptive attack in which an actor impersonates a trusted "
  "party in order to obtain sensitive information or to induce a victim to visit a malicious "
  "site (Anti-Phishing Working Group, 2025). The operative artefact is the URL, whose "
  "structure supplies the evidence a classifier can use before the destination is visited: a "
  "URL comprises a scheme, an authority, a path, an optional query and an optional fragment, "
  "and each of these components carries signals that distinguish hostile from legitimate "
  "addresses. Because phishing attempts are short-lived and use freshly registered domains "
  "(Rashid et al., 2024), the signal that would be most reliable \u2014 the reputation of the "
  "domain \u2014 is precisely the signal that does not yet exist at the moment of the attack, "
  "which is why a structural classifier is required alongside reputation data rather than "
  "instead of it.")
p("Theoretical framework. The study is grounded in statistical learning theory and in "
  "ensemble learning. Statistical learning theory addresses inference from finite samples, "
  "distinguishing empirical risk, the error measured on training data, from true risk, the "
  "error on the underlying distribution, and shows that the gap between them depends on the "
  "capacity of the model class rather than on training error alone (Vapnik, 1999). The "
  "distinction governs the design of this study: a measured accuracy is meaningful only when "
  "computed on data that played no part in training, and two algorithms may be compared only "
  "when both are trained and tested under identical conditions. Ensemble learning provides "
  "the mechanism by which a collection of unstable learners is combined into a stable "
  "predictor; averaging across trees grown on bootstrap samples with random feature selection "
  "reduces variance without materially increasing bias (Breiman, 2001), which explains the "
  "resistance of random forest to the overfitting a single deep tree would exhibit. The same "
  "account explains why logistic regression remains a worthwhile comparison, trading the "
  "flexibility of the ensemble for transparency and speed.")
p("Empirical review. Abutaha, Ababneh, Mahmoud and Al-Haj Baddar (2021) investigated "
  "detection based on lexical analysis, generating 22 features from URL strings and training "
  "four classifiers, of which a support vector machine achieved the highest accuracy at 99.89 "
  "per cent on a dataset that originally contained 1,056,937 labelled URLs; their comparison "
  "shows that the ranking of algorithms is an empirical result rather than a foregone "
  "conclusion. Bahaghighat, Ghasemi and Ozen (2023) compared several algorithms under a "
  "shared data-preparation pipeline, establishing that when algorithms are compared under "
  "identical conditions the difference in outcome is attributable to the algorithms "
  "themselves. Aung and Yamana (2024) addressed inadequate tokenisation and dependence on "
  "dataset-specific lexical features by replacing them with dataset-independent natural "
  "language features, and their hybrid model achieved between 95.41 and 99.76 per cent "
  "accuracy across five open datasets; the spread across datasets is itself instructive, "
  "because a well-built model on unfamiliar data lands in the mid-nineties rather than at the "
  "upper limit. Ghalechyan, Israyelyan, Arakelyan, Hovhannisyan and Davtyan (2024) "
  "demonstrated a model operating in production against daily-validated URLs at approximately "
  "97 per cent accuracy, and note that individual labels could not be verified at that volume, "
  "which tempers any claim that a figure obtained on a clean academic dataset transfers "
  "directly to live traffic. Rashid, Doyle, Han and Seneviratne (2024) show that detectors "
  "which perform well when the test set is drawn from the same dataset as the training set "
  "lose effectiveness on data from another source, and propose unsupervised domain adaptation "
  "as a remedy. Yi, Omotosho and Balogun (2026) tested three ensemble algorithms across four "
  "secondary datasets and applied the SHapley Additive exPlanations framework to interpret "
  "individual decisions, concluding that per-prediction explanations strengthen the "
  "credibility of a detector.")
p("Gap in the literature. Reported accuracies range from the mid-nineties to the high "
  "nineties depending on dataset, features and algorithm, and accuracy degrades when "
  "evaluation moves away from the training distribution. Two gaps follow. The first is "
  "methodological: comparative results are rarely produced under identical preprocessing, "
  "identical features and an identical evaluation protocol, so the choice of algorithm for a "
  "lightweight, deployable, URL-only tool lacks direct evidence. The second is practical: few "
  "of these detectors are delivered as tools that a non-technical user can operate, and fewer "
  "still present a verdict together with the evidence behind it or with an honest statement of "
  "the conditions under which the verdict should not be trusted. This study addresses both, "
  "and adds a local dimension by assembling a Nigerian allow-list, since the global "
  "popularity data on which reputation layers depend contains no Nigerian domain within its "
  "first 100,000 ranks.")

# ============================================================ 8. METHODOLOGY
h("8. Methodology")
p("Research design. The study adopts an experimental research design together with a "
  "developmental component. The experiment manipulates two factors under controlled "
  "conditions: the learning algorithm, at two levels, and the evaluation distribution, at two "
  "levels, being data drawn from the same collection as the training set and data drawn from "
  "independent sources. The developmental component produces the artefact that makes the "
  "study's claims testable by a user rather than only by an experimenter. The "
  "Cross-Industry Standard Process for Data Mining guides the machine-learning work, "
  "providing an ordered sequence of business understanding, data understanding, data "
  "preparation, modelling, evaluation and deployment, and the application is developed "
  "incrementally with each functional increment tested against the requirement specification "
  "before the next is added. The study involves no human participants: all data are publicly "
  "available URL strings, and no personal data are collected.")
p("Population of the study. The population comprises web addresses. The accessible population "
  "is the PhiUSIIL collection of 235,795 labelled URLs (Prasad and Chandra, 2024), together "
  "with independent collections used to test behaviour outside that distribution: a "
  "community phishing feed, a commercial passive-DNS popularity list, and a set of legitimate "
  "URLs assembled from the home pages and sitemaps of well-known domains.")
p("Sample size and sampling technique. Duplicate addresses were removed from the collection, "
  "leaving 235,370 usable rows, from which a stratified random sample was drawn by class and "
  "divided into a training set and a held-out test set in a ratio of 80 to 20 per cent, with "
  "a fixed random seed so that the split is reproducible. Stratification preserves the class "
  "balance of the collection across both parts. External validation used samples drawn at "
  "random from sources that contributed nothing to training, and the field test that "
  "established the deployed configuration combined hostile addresses, bare domain names and "
  "legitimate addresses carrying paths. A summary of the evaluation sets is given in the "
  "table below.")
t = doc.add_table(rows=1, cols=3)
t.style = "Table Grid"
hdr = t.rows[0].cells
for cell, text in zip(hdr, ("Evaluation set", "Size", "Purpose")):
    cell.text = ""
    pr = cell.paragraphs[0]
    pr.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    _run(pr, text, bold=True)
for row in (
    ("Training set (PhiUSIIL)", "188,296", "Model fitting, identical for both algorithms"),
    ("Held-out test set (PhiUSIIL)", "47,074", "In-distribution comparison of the two algorithms"),
    ("Independent-source set", "1,000", "Behaviour on URLs from feeds that trained nothing"),
    ("Field test", "7,368", "Choice of deployed configuration; false-positive measurement"),
    ("Hard legitimate cases", "30", "Known difficult addresses, retained as a regression set"),
):
    cells = t.add_row().cells
    for cell, text in zip(cells, row):
        cell.text = ""
        pr = cell.paragraphs[0]
        pr.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        _run(pr, text)
centre()
p("Instrumentation. The measuring instrument is the feature extractor together with the "
  "learning algorithms it feeds: each submitted URL is reduced to the same fixed set of "
  "lexical and structural features used in training, and the trained model returns a "
  "probability that is thresholded to produce the class. Ground truth is supplied by the "
  "labels of the PhiUSIIL dataset for the primary evaluation and by the provenance of each "
  "address for the external sets, since a URL published in a community phishing feed and a "
  "URL drawn from a passive-DNS popularity list are labelled by their source rather than by "
  "inspection. The deployed web application is itself an instrument for the fifth research "
  "question, since response time and the clarity of the presented verdict can only be "
  "measured on the working system.")
p("Validity and reliability of the instrument. Construct validity rests on the fact that "
  "every feature is drawn from published URL-based detection work rather than invented for "
  "this study, and on the exclusion of the dataset's content-derived columns so that the "
  "model's inputs match those available to the deployed tool. Internal validity rests on "
  "identical preprocessing, an identical split and an identical protocol for both "
  "algorithms, so that any difference in outcome is attributable to the algorithm rather "
  "than to the preparation. External validity is tested rather than assumed, by evaluation "
  "on independent sources and by an explicit refusal to claim that measured performance "
  "extends to live internet traffic. Reliability rests on the determinism of the pipeline: "
  "given the fixed seed and the stored configuration, the same inputs produce the same "
  "split, the same fitted models and the same reported metrics, and the model artefact, the "
  "metric files and the full source code are retained so that every figure reported can be "
  "regenerated.")
p("Method of data analysis. Descriptive statistics are used to characterise the collection "
  "and the derived features. Classifier performance is reported as accuracy, precision, "
  "recall, F1-score and confusion matrices, computed on the held-out test set and again on "
  "the independent-source set so that the two conditions can be compared directly. The "
  "decision threshold is analysed across its range rather than assumed, an ablation over the "
  "feature set establishes which features carry the classification, and the field test "
  "supplies the false-positive and detection rates on addresses outside the collection. "
  "Where a reputation layer alters a verdict, its effect is measured separately from the "
  "model's, because the layer is a presentation rule and not a feature of the classifier. "
  "The algorithm deployed is the one that performs better under the field-test rule stated "
  "in advance, with ties broken by the lower false-positive rate on legitimate URLs that "
  "carry a path and then by higher recall on hostile URLs.")

# ============================================================= 9. STATUS
h("9. Status of the Study")
p("This proposal records the study as approved and as executed. The system it describes has "
  "been implemented, deployed and evaluated; the measured results appear in full in the "
  "project report, whose appendices reproduce the source code of the classification service "
  "and of the training pipeline from which those results were produced. For the avoidance of "
  "doubt about the stage of the work, the principal measured outcomes are as follows. On the "
  "held-out portion of the PhiUSIIL collection the random forest classified at 99.59 per cent "
  "accuracy, against 98.92 per cent for logistic regression, with a precision of 99.88 per "
  "cent, a recall of 99.15 per cent and an F1-score of 99.52 per cent. On the same model, "
  "accuracy fell to 66.60 per cent when the test set was drawn from independent sources, "
  "which confirms the generalisation gap reported in the literature. On the field test the "
  "corrected deployed model reaches 88.44 per cent accuracy, rising to an upper bound of "
  "95.48 per cent when the reputation layer is accounted for, while hostile recall on that "
  "same test falls from 93.50 to 81.10 per cent; the correction that produced this trade-off "
  "reduced false positives on legitimate addresses carrying paths from 100 to 41.59 per cent, "
  "and a domain-first presentation rule reduced them further to 3.00 per cent. The curated "
  "Nigerian allow-list of 99 entries clears all thirty hard legitimate cases, and a bundled "
  "blocklist of 112,433 hostile domains, which may support an accusation but never create or "
  "clear one, recovered 1.72 per cent of the accusations it was able to examine on one "
  "independent feed and none on the other. The tool is live and can be examined at "
  "https://aabo-ai.vercel.app.")

# ============================================================ 10. REFERENCES
h("10. References")
for r in (
    "Abutaha, M., Ababneh, M., Mahmoud, K., & Al-Haj Baddar, S. W. (2021). URL phishing "
    "detection using machine learning techniques based on URLs lexical analysis. In 2021 12th "
    "International Conference on Information and Communication Systems (ICICS) (pp. 1\u20136). "
    "IEEE. https://doi.org/10.1109/ICICS52457.2021.9464539",
    "Anti-Phishing Working Group. (2025). Phishing activity trends report: 1st quarter 2025. "
    "https://docs.apwg.org/reports/apwg_trends_report_q1_2025.pdf",
    "Aung, E. S., & Yamana, H. (2024). PhiSN: Phishing URL detection using segmentation and "
    "NLP features. Journal of Information Processing, 32, 973\u2013989. "
    "https://doi.org/10.2197/ipsjjip.32.973",
    "Bahaghighat, M., Ghasemi, M., & Ozen, F. (2023). A high-accuracy phishing website "
    "detection method based on machine learning. Journal of Information Security and "
    "Applications, 77, Article 103553. https://doi.org/10.1016/j.jisa.2023.103553",
    "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5\u201332. "
    "https://doi.org/10.1023/A:1010933404324",
    "Ejalonibu, G., Obot, E., & Nandi, L. (2026). Electronic payment fraud trends in "
    "Nigeria's banking sector: 2025 data, emerging risks, and legislative imperatives (Data "
    "Brief). National Institute for Legislative and Democratic Studies. "
    "https://ir.nilds.gov.ng",
    "Ghalechyan, H., Israyelyan, E., Arakelyan, A., Hovhannisyan, G., & Davtyan, A. (2024). "
    "Phishing URL detection with neural networks: An empirical study. Scientific Reports, "
    "14, Article 25134. https://doi.org/10.1038/s41598-024-74725-6",
    "Prasad, A., & Chandra, S. (2024). PhiUSIIL: A diverse security profile empowered phishing "
    "URL detection framework based on similarity index and incremental learning. Computers & "
    "Security, 136, Article 103545. https://doi.org/10.1016/j.cose.2023.103545",
    "Rashid, F., Doyle, B., Han, S. C., & Seneviratne, S. (2024). Phishing URL detection "
    "generalisation using unsupervised domain adaptation. Computer Networks, 245, Article "
    "110398. https://doi.org/10.1016/j.comnet.2024.110398",
    "Vapnik, V. N. (1999). An overview of statistical learning theory. IEEE Transactions on "
    "Neural Networks, 10(5), 988\u2013999. https://doi.org/10.1109/72.788640",
    "Yi, L., Omotosho, A., & Balogun, H. (2026). Phishing URL detection and interpretability "
    "with machine learning: A cross-dataset approach. Security and Privacy, 9(1), Article "
    "e70175. https://doi.org/10.1002/spy2.70175",
):
    ref(r)

doc.save(OUT)

# ------------------------------------------------------------------- report
d2 = Document(OUT)
words = sum(len(x.text.split()) for x in d2.paragraphs)
print("saved:", OUT)
print("paragraphs:", len(d2.paragraphs), "| words:", words,
      "| tables:", len(d2.tables))
print("title words:", len(TITLE.split()), "(NOUN limit 23)")
