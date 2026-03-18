import { siteConfig } from "@/shared/lib/config/site";

export interface LegalSection {
  title: string;
  paragraphs: string[];
  bullets?: string[];
}

export interface LegalDocument {
  slug: string;
  title: string;
  shortTitle: string;
  description: string;
  summary: string;
  sections: LegalSection[];
}

const lastUpdated = "March 18, 2026";
const legalEntityName =
  siteConfig.organization.legalName || siteConfig.organization.name || siteConfig.appName || "Talk2Record";
const supportEmail =
  siteConfig.contact.supportEmail || siteConfig.organization.email || "support@talk2record.com";
const addressParts = [
  siteConfig.organization.address.street,
  siteConfig.organization.address.city,
  siteConfig.organization.address.region,
  siteConfig.organization.address.postalCode,
  siteConfig.organization.address.country,
].filter(Boolean);
const businessAddress = addressParts.length > 0 ? addressParts.join(", ") : "Business address available on request";
const governingLawCountry = siteConfig.organization.address.country || "the applicable jurisdiction";

export const legalLastUpdated = lastUpdated;
export const legalContactEmail = supportEmail;
export const legalBusinessAddress = businessAddress;
export const legalEntity = legalEntityName;

export const legalDocuments: LegalDocument[] = [
  {
    slug: "privacy-policy",
    title: `Privacy Policy - ${legalEntityName}`,
    shortTitle: "Privacy Policy",
    description:
      "How Talk2Record collects, uses, safeguards, transfers, and deletes personal data for its AI-powered SaaS.",
    summary:
      "This Privacy Policy explains how Talk2Record handles account data, voice content, technical data, and billing-related information in line with global SaaS privacy expectations.",
    sections: [
      {
        title: "Controller Information",
        paragraphs: [
          `${legalEntityName} acts as the data controller for personal data processed through the public website, product operations, and account administration activities described in this policy.`,
          `You can contact us at ${supportEmail}. Our business address is ${businessAddress}.`,
        ],
      },
      {
        title: "Data We Collect",
        paragraphs: [
          "We collect information that is necessary to operate the platform, secure the service, administer subscriptions, and support customer success.",
        ],
        bullets: [
          "Account data, such as name, email address, workspace details, and company information.",
          "Voice and content data, such as uploaded audio files, transcripts, extracted records, notes, and review actions.",
          "Technical data, such as IP address, browser and device information, logs, session events, and service diagnostics.",
          "Billing data handled through third-party payment providers, such as Stripe or Paddle, including subscription status, invoices, and limited transaction metadata.",
        ],
      },
      {
        title: "Legal Basis for Processing",
        paragraphs: [
          "Where the GDPR or similar laws apply, we rely on one or more lawful bases depending on the processing activity.",
        ],
        bullets: [
          "Contract, when processing is required to provide the service you requested, authenticate users, maintain workspaces, and deliver core product functionality.",
          "Legitimate interests, when processing is necessary for analytics, fraud prevention, service monitoring, abuse detection, and product security, provided those interests are not overridden by your rights.",
          "Consent, when required for marketing communications, optional cookies, or specific features that depend on opt-in behavior.",
          "Legal obligation, when we must retain or disclose information for tax, accounting, regulatory, or law-enforcement purposes.",
        ],
      },
      {
        title: "AI Processing Disclosure",
        paragraphs: [
          "Talk2Record uses AI systems to transcribe speech, classify content, and extract structured business records from voice inputs and related text.",
          "To deliver those features, customer data may be processed by carefully selected AI providers, including OpenAI and Google Gemini or functionally similar providers used to operate the service.",
          "We do not use customer content to train third-party foundation models unless we clearly state otherwise and provide any required notice or choice.",
          "AI-generated outputs may be incomplete, inaccurate, or contextually incorrect and should be reviewed before use in operational, financial, or compliance workflows.",
        ],
      },
      {
        title: "Automated Decision-Making",
        paragraphs: [
          "Our systems may generate automated recommendations, structured outputs, confidence scores, and workflow suggestions based on submitted content.",
          "You remain able to review, edit, reject, or request human review of those outputs. Where applicable law grants additional rights relating to automated decision-making, we will support those rights.",
        ],
      },
      {
        title: "Subprocessors",
        paragraphs: [
          "We use third-party processors and subprocessors to host infrastructure, run AI workloads, process payments, send transactional communications, and measure product usage.",
          "These providers may include cloud infrastructure providers, AI model providers, payment processors, analytics vendors, and security tooling. A current subprocessor list is available upon request.",
        ],
      },
      {
        title: "International Transfers",
        paragraphs: [
          "Because we operate as a global SaaS business, personal data may be transferred to or accessed from countries outside the country where the data was originally collected.",
          "When required, we implement appropriate safeguards such as Standard Contractual Clauses, contractual confidentiality obligations, vendor due diligence, and secure cloud controls designed to protect transferred data.",
        ],
      },
      {
        title: "Data Retention",
        paragraphs: [
          "We retain personal data for as long as necessary to provide the service, maintain records, resolve disputes, enforce agreements, and comply with legal obligations.",
          "Account and workspace data is generally retained while an account remains active and for a limited period afterward as needed for backup, audit, fraud prevention, and lawful recordkeeping.",
          "Some service providers, including AI providers, may retain limited logs for a short period for security, abuse prevention, and platform reliability purposes.",
        ],
      },
      {
        title: "Security Measures",
        paragraphs: [
          "We maintain administrative, technical, and organizational measures designed to protect personal data against unauthorized access, disclosure, alteration, and destruction.",
        ],
        bullets: [
          "Encryption in transit and, where supported, encryption at rest.",
          "Role-based access controls and least-privilege operational practices.",
          "Monitoring, logging, and anomaly detection for service integrity and security review.",
          "Incident response procedures and vendor oversight for critical systems.",
        ],
      },
      {
        title: "Your Rights",
        paragraphs: [
          "Depending on your location, you may have rights to access, correct, delete, restrict, object to, or export certain personal data, as well as rights to withdraw consent where consent is the legal basis.",
          `To exercise these rights, contact ${supportEmail}. We may request reasonable verification before fulfilling a request.`,
        ],
      },
      {
        title: "Data Ownership",
        paragraphs: [
          "Customers retain ownership of the content and business data they submit to Talk2Record.",
          "We process that data only to provide, secure, maintain, and improve the contracted service, subject to this policy and any applicable data processing agreement.",
        ],
      },
      {
        title: "Updates and Contact",
        paragraphs: [
          "We may update this Privacy Policy from time to time to reflect legal, technical, or business changes. If we make material changes, we will update the last updated date and provide additional notice where required.",
          `Questions about this policy can be sent to ${supportEmail}.`,
        ],
      },
    ],
  },
  {
    slug: "terms-of-service",
    title: `Terms of Service - ${legalEntityName}`,
    shortTitle: "Terms of Service",
    description:
      "The contractual terms governing access to Talk2Record, including billing, AI disclaimers, acceptable use, and liability protections.",
    summary:
      "These Terms of Service govern access to Talk2Record and allocate responsibilities around AI outputs, user submissions, payments, platform use, and legal risk.",
    sections: [
      {
        title: "Acceptance",
        paragraphs: [
          "By accessing or using Talk2Record, you agree to be bound by these Terms of Service and any additional policies or order forms that apply to your use of the service.",
          "If you use the service on behalf of an organization, you represent that you have authority to bind that organization to these terms.",
        ],
      },
      {
        title: "Service Description",
        paragraphs: [
          "Talk2Record is a subscription-based software service that converts voice inputs and related information into transcripts, structured records, analytics, and operational workflows using AI-assisted processing.",
        ],
      },
      {
        title: "User Responsibilities",
        paragraphs: [
          "You are responsible for your account, your users, and the legality of the content you submit to the service.",
        ],
        bullets: [
          "You must have all necessary rights, notices, and consents to submit voice data and related personal data for processing.",
          "You must not upload unlawful, infringing, deceptive, harmful, or malicious content.",
          "You must comply with applicable privacy, employment, consumer protection, telecom, and AI-related laws that apply to your use case.",
        ],
      },
      {
        title: "AI Disclaimer",
        paragraphs: [
          "The service uses AI and machine learning systems to generate outputs. Those outputs are probabilistic and may contain errors, omissions, or incorrect inferences.",
          "You are solely responsible for reviewing and verifying outputs before relying on them for inventory decisions, financial operations, compliance reporting, customer communication, or any other consequential use.",
        ],
      },
      {
        title: "Prohibited Use",
        paragraphs: [
          "You may not use Talk2Record for unlawful, abusive, or high-risk activity that exceeds the intended scope of the service.",
        ],
        bullets: [
          "Fraud, deception, or impersonation.",
          "Surveillance, covert monitoring, or unauthorized tracking.",
          "Processing personal data without a lawful basis or required consent.",
          "Any activity that violates sanctions, export controls, intellectual property rights, or applicable law.",
        ],
      },
      {
        title: "Data Responsibility",
        paragraphs: [
          "You remain responsible for the accuracy, legality, and appropriateness of the data submitted to the service and for the decisions taken based on outputs generated by the service.",
        ],
      },
      {
        title: "Payments",
        paragraphs: [
          "Paid plans are billed on a subscription basis and renew automatically unless cancelled before the end of the current billing period.",
          "Pricing may vary by region, currency, plan configuration, taxes, discounts, or reseller arrangements. Unless otherwise required by law or expressly agreed in writing, fees are non-refundable.",
        ],
      },
      {
        title: "Intellectual Property",
        paragraphs: [
          "We retain all rights, title, and interest in the Talk2Record platform, software, documentation, branding, and service improvements, excluding customer data.",
          "You retain ownership of your submitted data and any outputs to the extent permitted by law and your agreements with third parties.",
        ],
      },
      {
        title: "Limitation of Liability",
        paragraphs: [
          "To the maximum extent permitted by law, Talk2Record and its affiliates will not be liable for indirect, incidental, special, consequential, exemplary, or punitive damages, or for loss of profits, revenue, goodwill, data, business opportunity, or anticipated savings.",
          "We are not responsible for losses arising from AI inaccuracies, customer misuse, unauthorized access caused by compromised credentials, third-party platform outages, or force majeure events.",
          "Nothing in these terms excludes liability that cannot legally be limited or excluded under applicable law.",
        ],
      },
      {
        title: "Indemnification",
        paragraphs: [
          "You agree to defend, indemnify, and hold harmless Talk2Record, its affiliates, and their personnel from claims, liabilities, damages, judgments, settlements, costs, and expenses arising from or related to your misuse of the service, your submitted data, your violation of law, or your infringement of third-party rights.",
        ],
      },
      {
        title: "Termination",
        paragraphs: [
          "We may suspend or terminate access to the service if you violate these terms, create material legal or security risk, fail to pay fees when due, or use the service in a way that could harm the platform, other users, or third parties.",
          "You may stop using the service at any time, subject to any billing commitments or notice periods in your subscription terms.",
        ],
      },
      {
        title: "Governing Law",
        paragraphs: [
          `These terms are governed by the laws of ${governingLawCountry}, excluding conflict-of-law rules, unless a different governing law is required by a signed commercial agreement.`,
        ],
      },
      {
        title: "Updates",
        paragraphs: [
          "We may modify these terms from time to time. Updated terms become effective when posted unless a later effective date is stated. Continued use of the service after the effective date constitutes acceptance of the updated terms.",
        ],
      },
    ],
  },
  {
    slug: "data-processing-agreement",
    title: `Data Processing Agreement - ${legalEntityName}`,
    shortTitle: "Data Processing Agreement",
    description:
      "Talk2Record's standard DPA terms for controller-processor relationships, security controls, subprocessors, and international transfers.",
    summary:
      "This DPA describes how Talk2Record processes customer personal data on behalf of customers, including security commitments, subprocessor controls, and support for data subject rights.",
    sections: [
      {
        title: "Roles",
        paragraphs: [
          "For customer personal data processed through the service, the customer acts as the controller or business, and Talk2Record acts as the processor or service provider, except where Talk2Record acts as an independent controller for its own account, security, billing, or legal compliance data.",
        ],
      },
      {
        title: "Scope and Instructions",
        paragraphs: [
          "We process customer personal data only to provide the service, maintain the platform, secure systems, troubleshoot issues, deliver agreed analytics, and comply with documented lawful instructions from the customer.",
          "If we believe a customer instruction violates applicable data protection law, we may notify the customer and suspend the affected processing where appropriate.",
        ],
      },
      {
        title: "Subprocessors",
        paragraphs: [
          "We may engage subprocessors to provide infrastructure, AI processing, payment support, communications, analytics, and security services necessary to operate Talk2Record.",
          "We require subprocessors to protect customer personal data through contractual obligations that are materially consistent with this DPA. We will provide subprocessor information and notice of material changes where required by law or contract.",
        ],
      },
      {
        title: "Security",
        paragraphs: [
          "We implement appropriate technical and organizational measures designed to protect customer personal data, taking into account the nature of the processing, the state of the art, implementation costs, and the risks to individuals.",
        ],
        bullets: [
          "Encryption in transit and other data protection controls appropriate to the environment.",
          "Access controls, authentication safeguards, and administrative segregation of duties.",
          "Operational monitoring, logging, backup, and resilience practices.",
          "Security review processes for critical vendors and infrastructure.",
        ],
      },
      {
        title: "Data Subject Rights",
        paragraphs: [
          "To the extent legally required and taking into account the nature of the processing, we will provide reasonable assistance to help customers respond to requests from data subjects to access, correct, delete, restrict, object to, or port their personal data.",
        ],
      },
      {
        title: "Breach Notification",
        paragraphs: [
          "We will notify customers without undue delay after becoming aware of a confirmed personal data breach affecting customer personal data.",
          "Where reasonably possible based on the information available at the time, our target is to provide initial notice within 72 hours of confirming a reportable incident, followed by supplementary updates as the investigation continues.",
        ],
      },
      {
        title: "Deletion and Return",
        paragraphs: [
          "Upon termination or expiration of the service, we will delete or return customer personal data within a reasonable timeframe, unless retention is required by law, needed for legitimate security backup cycles, or necessary to establish, exercise, or defend legal claims.",
        ],
      },
      {
        title: "International Transfers",
        paragraphs: [
          "If customer personal data is transferred internationally, we will rely on lawful transfer mechanisms such as Standard Contractual Clauses, adequacy decisions, or equivalent safeguards recognized under applicable law.",
        ],
      },
    ],
  },
  {
    slug: "ai-usage-disclaimer",
    title: `AI Usage and Disclaimer - ${legalEntityName}`,
    shortTitle: "AI Usage and Disclaimer",
    description:
      "How Talk2Record uses AI systems, what their limits are, and what users must do before relying on AI outputs.",
    summary:
      "This policy explains the AI features inside Talk2Record, the limits of model-generated outputs, and the user's responsibility to independently verify results.",
    sections: [
      {
        title: "AI Processing",
        paragraphs: [
          "Talk2Record uses AI systems to transcribe voice recordings, detect business-relevant entities, extract structured records, and support workflow automation.",
          "Different models or vendors may be used over time to improve performance, availability, language support, and cost efficiency.",
        ],
      },
      {
        title: "Limitations",
        paragraphs: [
          "AI outputs are inherently probabilistic. They may be inaccurate, incomplete, inconsistent, out of date, or overly confident.",
          "Speech accents, poor audio quality, multilingual content, domain-specific terms, and ambiguous context can increase the risk of incorrect transcription or extraction.",
        ],
      },
      {
        title: "No Professional Advice",
        paragraphs: [
          "Outputs from Talk2Record do not constitute legal advice, financial advice, accounting advice, tax advice, regulatory advice, or any other professional advice.",
        ],
      },
      {
        title: "User Responsibility",
        paragraphs: [
          "Users must apply independent judgment and verify AI outputs before using them in commercial, operational, compliance, customer-facing, or other high-impact decisions.",
        ],
      },
      {
        title: "Bias and Risk",
        paragraphs: [
          "AI systems may reflect biases present in data, model design, or operating context. They may also fail in edge cases or generate materially misleading outputs.",
          "Customers should implement human review, validation logic, and risk-based controls appropriate to their use case.",
        ],
      },
      {
        title: "Accountability",
        paragraphs: [
          "Customers remain responsible for the actions they take based on AI outputs and for determining whether Talk2Record is appropriate for their use case, regulatory environment, and risk tolerance.",
        ],
      },
    ],
  },
  {
    slug: "cookie-policy",
    title: `Cookie Policy - ${legalEntityName}`,
    shortTitle: "Cookie Policy",
    description:
      "Information about how Talk2Record uses cookies and similar technologies for authentication, analytics, and performance.",
    summary:
      "This Cookie Policy explains which categories of cookies Talk2Record uses, why they are used, and how users can control them.",
    sections: [
      {
        title: "What We Use Cookies For",
        paragraphs: [
          "We use cookies and similar technologies to keep users signed in, remember preferences, understand service usage, and improve reliability and performance.",
        ],
        bullets: [
          "Essential cookies for authentication, session continuity, security, and fraud prevention.",
          "Preference cookies for settings such as theme, language, or other saved experience choices.",
          "Analytics cookies to understand product usage, traffic, and performance trends.",
          "Performance cookies to support load balancing, diagnostics, and service optimization.",
        ],
      },
      {
        title: "Consent",
        paragraphs: [
          "Where required by law, we request consent before placing non-essential cookies or similar technologies on a device.",
          "Essential cookies that are strictly necessary to provide the service may be used without consent where permitted by law.",
        ],
      },
      {
        title: "Managing Cookies",
        paragraphs: [
          "You can control cookies through your browser settings, device controls, and any cookie preferences made available in the product experience.",
          "Disabling certain cookies may affect functionality, login persistence, analytics accuracy, or parts of the user experience.",
        ],
      },
    ],
  },
  {
    slug: "acceptable-use-policy",
    title: `Acceptable Use Policy - ${legalEntityName}`,
    shortTitle: "Acceptable Use Policy",
    description:
      "Rules for permitted and prohibited use of Talk2Record, including privacy-sensitive misuse and abusive activity.",
    summary:
      "This Acceptable Use Policy describes prohibited activity on Talk2Record and the consequences of misuse.",
    sections: [
      {
        title: "Prohibited Activity",
        paragraphs: [
          "You may not use Talk2Record in ways that are illegal, harmful, abusive, deceptive, or inconsistent with the intended purpose of the service.",
        ],
        bullets: [
          "Uploading or processing data without a lawful basis, valid notice, or required consent.",
          "Processing sensitive personal data unlawfully or in a way that creates unreasonable risk to individuals.",
          "Using the service for surveillance, covert recording, stalking, or unauthorized tracking.",
          "Attempting to reverse engineer, disrupt, overload, probe, or abuse system resources, rate limits, or security controls.",
          "Using the service to generate or support fraud, harassment, disinformation, or other unlawful conduct.",
        ],
      },
      {
        title: "Enforcement",
        paragraphs: [
          "Violations of this policy may lead to content removal, feature restrictions, suspension, termination, or referral to competent authorities where appropriate.",
        ],
      },
    ],
  },
  {
    slug: "billing-policy",
    title: `Billing Policy - ${legalEntityName}`,
    shortTitle: "Billing Policy",
    description:
      "The billing rules for Talk2Record subscriptions, renewals, currencies, failed payments, taxes, and refunds.",
    summary:
      "This Billing Policy explains how Talk2Record charges subscriptions, handles renewals, supports multiple currencies, and manages failed payments and refunds.",
    sections: [
      {
        title: "Subscriptions and Renewal",
        paragraphs: [
          "Talk2Record plans are billed on a recurring subscription basis. Unless otherwise stated, subscriptions renew automatically at the end of each billing cycle until cancelled.",
        ],
      },
      {
        title: "Currencies and Regional Pricing",
        paragraphs: [
          "We may offer multi-currency pricing, region-based pricing, localized taxes, or reseller pricing structures depending on customer location and payment method.",
          "Displayed prices may exclude taxes, duties, levies, or bank charges unless expressly stated otherwise.",
        ],
      },
      {
        title: "Payment Processing",
        paragraphs: [
          "Payments may be processed through third-party billing providers such as Stripe or Paddle. Your use of those payment methods may also be subject to the provider's terms and privacy notices.",
        ],
      },
      {
        title: "Failed Payments and Suspension",
        paragraphs: [
          "If a payment fails, we may retry the charge, request an updated payment method, pause premium features, or suspend access until outstanding amounts are paid.",
        ],
      },
      {
        title: "Refunds",
        paragraphs: [
          "Except where required by law, contract, or an explicit written offer, subscription fees are non-refundable and partial billing periods are not prorated for refunds.",
        ],
      },
      {
        title: "Plan Changes and Cancellation",
        paragraphs: [
          "Upgrades, downgrades, seat changes, or usage-based adjustments may take effect immediately or at the next renewal date, depending on the billing model in use.",
          "You may cancel renewal at any time, and cancellation will generally take effect at the end of the current paid billing term unless otherwise required by law.",
        ],
      },
    ],
  },
];

export const legalDocumentsBySlug = new Map(legalDocuments.map((document) => [document.slug, document]));

export function getLegalDocument(slug: string) {
  return legalDocumentsBySlug.get(slug);
}
