export type OnboardingProfile = {
  employment_status: 'employee' | 'freelancer' | 'both' | 'retired' | 'student' | 'unemployed';
  marital_status: 'single' | 'married';
  has_children: boolean;
  num_children: number;
  rental_income: boolean;
  capital_gains: boolean;
  foreign_income: boolean;
  home_office_days: number;
  commute_km: number;
  commute_days: number;
  donations_eur: number;
  has_insurance_expenses: boolean;
  has_haushaltsnahe: boolean;
  has_handwerker: boolean;
  church_member: boolean;
  bundesland: string;
  tax_class: number;
};

export const EMPTY_PROFILE: OnboardingProfile = {
  employment_status: 'employee',
  marital_status: 'single',
  has_children: false,
  num_children: 0,
  rental_income: false,
  capital_gains: false,
  foreign_income: false,
  home_office_days: 0,
  commute_km: 0,
  commute_days: 230,
  donations_eur: 0,
  has_insurance_expenses: true,
  has_haushaltsnahe: false,
  has_handwerker: false,
  church_member: false,
  bundesland: 'Bayern',
  tax_class: 1,
};

export const BUNDESLAENDER = [
  'Baden-Wuerttemberg',
  'Bayern',
  'Berlin',
  'Brandenburg',
  'Bremen',
  'Hamburg',
  'Hessen',
  'Mecklenburg-Vorpommern',
  'Niedersachsen',
  'Nordrhein-Westfalen',
  'Rheinland-Pfalz',
  'Saarland',
  'Sachsen',
  'Sachsen-Anhalt',
  'Schleswig-Holstein',
  'Thueringen',
];

export function determineRequiredAnlagen(profile: OnboardingProfile): string[] {
  const required = ['Mantelbogen'];

  if (['employee', 'both', 'retired'].includes(profile.employment_status)) {
    required.push('Anlage N');
  }

  if (profile.employment_status === 'student') {
    // Students with Werkstudent/Minijob income may still need Anlage N
  }

  if (profile.employment_status === 'unemployed') {
    // ALG is tax-free but subject to Progressionsvorbehalt
  }

  if (profile.rental_income) {
    required.push('Anlage V');
  }

  if (profile.capital_gains) {
    required.push('Anlage KAP');
  }

  if (profile.has_children) {
    required.push('Anlage Kind');
  }

  if (profile.foreign_income) {
    required.push('Anlage AUS');
  }

  if (profile.has_insurance_expenses || ['employee', 'both', 'retired', 'student', 'unemployed'].includes(profile.employment_status)) {
    required.push('Anlage Vorsorge');
  }

  return required;
}

export function suggestQuickWins(profile: OnboardingProfile): string[] {
  const tips: string[] = [];

  if (profile.home_office_days > 0) {
    const capped = Math.min(profile.home_office_days, 210);
    tips.push(`Home office allowance: up to ${capped * 6} EUR (${capped} days x 6 EUR)`);
  }

  if (profile.commute_km > 0) {
    tips.push(`Commuting costs: Anlage N, Zeile 31 (${profile.commute_km} km)`);
  }

  if (profile.donations_eur > 0) {
    tips.push(`Donations of ${profile.donations_eur} EUR claimable as Sonderausgaben`);
  }

  if (profile.has_children) {
    tips.push('Childcare costs: 2/3 deductible, max 4,000 EUR per child');
  }

  if (profile.has_haushaltsnahe) {
    tips.push('Household services: 20% tax credit, max 4,000 EUR');
  }

  if (profile.has_handwerker) {
    tips.push('Craftsmen services: 20% tax credit, max 1,200 EUR');
  }

  tips.push('Bank account fees: flat 16 EUR deductible without receipts');

  return tips;
}
