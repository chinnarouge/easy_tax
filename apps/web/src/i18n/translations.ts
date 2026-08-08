export type Locale = 'de' | 'en';

type TranslationKeys = {
  heroTitle: string;
  heroBody: string;
  onboarding: string;
  dashboard: string;
  taxForm: string;
  documents: string;
  review: string;
  export: string;
  uploadLabel: string;
  exportPdf: string;
  exportCsv: string;
};

export const translations: Record<Locale, TranslationKeys> = {
  de: {
    heroTitle: 'Steuererklarung mit Fuhrung statt Ratselraten.',
    heroBody:
      'SteuerHelfer analysiert Ihre Dokumente, zeigt exakt welche ELSTER-Zeile jeder Wert gehoert, und schlaegt verpasste Abzuege vor.',
    onboarding: 'Onboarding',
    dashboard: 'Dashboard',
    taxForm: 'Steuerformular',
    documents: 'Dokumente',
    review: 'Prufen',
    export: 'Export',
    uploadLabel: 'Dokument hochladen',
    exportPdf: 'PDF-Mapping exportieren',
    exportCsv: 'CSV exportieren',
  },
  en: {
    heroTitle: 'Tax filing with guidance, not guesswork.',
    heroBody:
      'SteuerHelfer analyzes your documents, shows exactly which ELSTER form and line each value belongs to, and suggests missed deductions.',
    onboarding: 'Onboarding',
    dashboard: 'Dashboard',
    taxForm: 'Tax form',
    documents: 'Documents',
    review: 'Review',
    export: 'Export',
    uploadLabel: 'Upload document',
    exportPdf: 'Export PDF mapping',
    exportCsv: 'Export CSV',
  },
};
