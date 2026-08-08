import { useCallback, useEffect, useMemo, useState } from 'react';

import ElsterFieldHint from './components/ElsterFieldHint';
import { translations, type Locale } from './i18n/translations';
import { api, setToken } from './lib/api';
import {
  BUNDESLAENDER,
  EMPTY_PROFILE,
  determineRequiredAnlagen,
  suggestQuickWins,
  type OnboardingProfile,
} from './lib/onboarding';
import { estimateTax } from './lib/tax';

type Page = 'auth' | 'onboarding' | 'dashboard' | 'taxform' | 'documents' | 'expenses' | 'review' | 'export' | 'settings';

type AuthMode = 'login' | 'register';

type TaxReturn = {
  tax_return_id: string;
  tax_year: number;
  status: string;
  required_anlagen: string[];
  sections: Record<string, Record<string, unknown>>;
  completion: number;
};

type DeductionSuggestion = {
  title: string;
  amount_eur: number | null;
  form: string;
  line: string;
  reason: string;
  field_id: string;
};

type UploadedDoc = {
  document_id: string;
  file_name: string;
  classification: string;
  extracted_fields: Record<string, unknown>;
  confidence: number;
};

export function App() {
  const [locale, setLocale] = useState<Locale>('de');
  const t = translations[locale];

  // Auth
  const [page, setPage] = useState<Page>('auth');
  const [authMode, setAuthMode] = useState<AuthMode>('register');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authName, setAuthName] = useState('');
  const [authError, setAuthError] = useState('');
  const [userName, setUserName] = useState('');

  // Onboarding
  const [onboardingStep, setOnboardingStep] = useState(0);
  const [profile, setProfile] = useState<OnboardingProfile>({ ...EMPTY_PROFILE });

  // Tax return
  const [taxReturn, setTaxReturn] = useState<TaxReturn | null>(null);
  const [activeSection, setActiveSection] = useState('');
  const [sectionValues, setSectionValues] = useState<Record<string, string>>({});
  const [saveStatus, setSaveStatus] = useState('');

  // Deductions
  const [suggestions, setSuggestions] = useState<DeductionSuggestion[]>([]);

  // Documents
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDoc[]>([]);
  const [uploadStatus, setUploadStatus] = useState('');

  // Expenses
  type ExpenseCategory = { label_de: string; label_en: string; form: string; line: string; hint: string };
  type Expense = { expense_id: string; category: string; category_label: string; description: string; amount_eur: number; date: string; form: string; line: string; receipt_document_id: string | null };
  const [expenseCategories, setExpenseCategories] = useState<Record<string, ExpenseCategory>>({});
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [expenseTotals, setExpenseTotals] = useState<Record<string, number>>({});
  const [expenseGrandTotal, setExpenseGrandTotal] = useState(0);
  const [newExpenseCategory, setNewExpenseCategory] = useState('work_equipment');
  const [newExpenseDesc, setNewExpenseDesc] = useState('');
  const [newExpenseAmount, setNewExpenseAmount] = useState('');
  const [newExpenseDate, setNewExpenseDate] = useState('2025-01-01');
  const [expenseStatus, setExpenseStatus] = useState('');

  // LLM settings
  const [llmProvider, setLlmProvider] = useState('anthropic');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [llmStatus, setLlmStatus] = useState('');
  const [llmProviders, setLlmProviders] = useState<Record<string, { name: string; models: string[]; default_model: string }>>({});
  const [llmConfigured, setLlmConfigured] = useState(false);
  const [llmKeyPreview, setLlmKeyPreview] = useState('');

  // Tax estimate (local)
  const [estimateIncome, setEstimateIncome] = useState(50000);
  const estimate = useMemo(
    () =>
      estimateTax({
        taxableIncome: estimateIncome,
        filingType: profile.marital_status === 'married' ? 'joint' : 'single',
        churchTaxRate: profile.church_member ? 0.09 : 0,
      }),
    [estimateIncome, profile.marital_status, profile.church_member],
  );

  const requiredAnlagen = useMemo(() => determineRequiredAnlagen(profile), [profile]);
  const quickWins = useMemo(() => suggestQuickWins(profile), [profile]);

  // ── Auth handlers ──

  const handleAuth = useCallback(async () => {
    setAuthError('');
    try {
      if (authMode === 'register') {
        const res = await api.register(authEmail, authPassword, authName);
        setToken(res.token);
        setUserName(authName || authEmail);
      } else {
        const res = await api.login(authEmail, authPassword);
        setToken(res.token);
        setUserName(res.email);
      }
      setPage('onboarding');
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : 'Authentication failed');
    }
  }, [authMode, authEmail, authPassword, authName]);

  // ── Onboarding submit ──

  const handleOnboardingSubmit = useCallback(async () => {
    try {
      const res = await api.createTaxReturn(2025, profile as unknown as Record<string, unknown>);
      const full = await api.getTaxReturn(res.tax_return_id);
      setTaxReturn(full);
      setActiveSection(full.required_anlagen[0] || 'Mantelbogen');
      setPage('dashboard');
    } catch {
      const anlagen = determineRequiredAnlagen(profile);
      setTaxReturn({
        tax_return_id: 'local',
        tax_year: 2025,
        status: 'draft',
        required_anlagen: anlagen,
        sections: {},
        completion: 0,
      });
      setActiveSection(anlagen[0] || 'Mantelbogen');
      setPage('dashboard');
    }
  }, [profile]);

  // ── Section save ──

  const handleSaveSection = useCallback(async () => {
    if (!taxReturn) return;
    setSaveStatus('Saving...');
    try {
      const res = await api.updateSection(taxReturn.tax_return_id, activeSection, sectionValues);
      setTaxReturn((prev) => (prev ? { ...prev, sections: res.sections as TaxReturn['sections'], completion: res.completion } : prev));
      setSaveStatus('Saved');
    } catch {
      setSaveStatus('Save failed (backend offline — data kept locally)');
    }
  }, [taxReturn, activeSection, sectionValues]);

  // ── Load suggestions ──

  const loadSuggestions = useCallback(async () => {
    if (!taxReturn) return;
    try {
      const res = await api.getDeductionSuggestions(taxReturn.tax_return_id);
      setSuggestions(res.suggestions);
    } catch {
      setSuggestions([]);
    }
  }, [taxReturn]);

  useEffect(() => {
    if (page === 'review') loadSuggestions();
  }, [page, loadSuggestions]);

  // ── Document upload ──

  const handleUploadDocument = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploadStatus('Uploading...');
    for (let i = 0; i < files.length; i++) {
      try {
        const res = await api.uploadDocument(files[i]);
        setUploadedDocs((prev) => [...prev, res]);
      } catch {
        setUploadStatus(`Failed to upload ${files[i].name}`);
        return;
      }
    }
    setUploadStatus(`${files.length} file(s) uploaded`);
    e.target.value = '';
  }, []);

  // ── Expenses ──

  const loadExpenseCategories = useCallback(async () => {
    try {
      const res = await api.getExpenseCategories();
      setExpenseCategories(res.categories);
    } catch { /* offline */ }
  }, []);

  const loadExpenses = useCallback(async () => {
    if (!taxReturn) return;
    try {
      const res = await api.listExpenses(taxReturn.tax_return_id);
      setExpenses(res.expenses);
      setExpenseTotals(res.totals_by_category);
      setExpenseGrandTotal(res.grand_total);
    } catch { /* offline */ }
  }, [taxReturn]);

  useEffect(() => {
    if (page === 'expenses') {
      loadExpenseCategories();
      loadExpenses();
    }
  }, [page, loadExpenseCategories, loadExpenses]);

  const handleAddExpense = useCallback(async () => {
    if (!taxReturn || !newExpenseDesc.trim() || !newExpenseAmount) return;
    setExpenseStatus('Saving...');
    try {
      await api.addExpense(taxReturn.tax_return_id, {
        category: newExpenseCategory,
        description: newExpenseDesc,
        amount_eur: parseFloat(newExpenseAmount),
        date: newExpenseDate,
      });
      setNewExpenseDesc('');
      setNewExpenseAmount('');
      setExpenseStatus('Added');
      await loadExpenses();
    } catch (err: unknown) {
      setExpenseStatus(err instanceof Error ? err.message : 'Failed');
    }
  }, [taxReturn, newExpenseCategory, newExpenseDesc, newExpenseAmount, newExpenseDate, loadExpenses]);

  const handleDeleteExpense = useCallback(async (expenseId: string) => {
    if (!taxReturn) return;
    try {
      await api.deleteExpense(taxReturn.tax_return_id, expenseId);
      await loadExpenses();
    } catch { /* offline */ }
  }, [taxReturn, loadExpenses]);

  // ── LLM settings ──

  const loadLlmProviders = useCallback(async () => {
    try {
      const res = await api.getLlmProviders();
      setLlmProviders(res.providers);
    } catch { /* offline */ }
  }, []);

  const loadLlmSettings = useCallback(async () => {
    try {
      const res = await api.getLlmSettings();
      setLlmConfigured(res.configured);
      if (res.configured) {
        setLlmProvider(res.provider || 'anthropic');
        setLlmModel(res.model_name || '');
        setLlmKeyPreview(res.key_preview || '');
      }
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    if (page === 'settings') {
      loadLlmProviders();
      loadLlmSettings();
    }
  }, [page, loadLlmProviders, loadLlmSettings]);

  const handleSaveLlm = useCallback(async () => {
    if (!llmApiKey.trim()) {
      setLlmStatus('Please enter an API key');
      return;
    }
    setLlmStatus('Saving...');
    try {
      const res = await api.saveLlmSettings(llmProvider, llmApiKey, llmModel);
      setLlmConfigured(true);
      setLlmKeyPreview(res.key_preview);
      setLlmApiKey('');
      setLlmStatus(`Saved: ${res.provider} / ${res.model_name}`);
    } catch (err: unknown) {
      setLlmStatus(err instanceof Error ? err.message : 'Failed to save');
    }
  }, [llmProvider, llmApiKey, llmModel]);

  const handleDeleteLlm = useCallback(async () => {
    try {
      await api.deleteLlmSettings();
      setLlmConfigured(false);
      setLlmKeyPreview('');
      setLlmStatus('API key removed');
    } catch { /* offline */ }
  }, []);

  // ── ELSTER hint for active section ──

  const sectionHint = useMemo(() => {
    const hints: Record<string, { title: string; form: string; line: string; detail: string }> = {
      Mantelbogen: {
        title: 'Personal data',
        form: 'Mantelbogen',
        line: 'Zeilen 1-17',
        detail: 'Identity, address, bank details, and filing metadata.',
      },
      'Anlage N': {
        title: 'Employment income',
        form: 'Anlage N',
        line: 'Zeile 6',
        detail: 'Gross salary from Lohnsteuerbescheinigung item 3, plus all Werbungskosten.',
      },
      'Anlage V': {
        title: 'Rental income',
        form: 'Anlage V',
        line: 'Zeile 9',
        detail: 'Total rental income and deductible expenses per property.',
      },
      'Anlage KAP': {
        title: 'Capital income',
        form: 'Anlage KAP',
        line: 'Zeile 7',
        detail: 'Investment income, withheld tax, and Sparerpauschbetrag.',
      },
      'Anlage Kind': {
        title: 'Child-related deductions',
        form: 'Anlage Kind',
        line: 'Zeile 6',
        detail: 'One Anlage Kind per child — childcare, school fees, Kindergeld.',
      },
      'Anlage Vorsorge': {
        title: 'Insurance contributions',
        form: 'Anlage Vorsorge',
        line: 'Zeile 4',
        detail: 'Pension, health, long-term care, and unemployment insurance.',
      },
      'Anlage AUS': {
        title: 'Foreign income',
        form: 'Anlage AUS',
        line: 'Zeile 4',
        detail: 'Income earned abroad and foreign tax credits.',
      },
    };
    return hints[activeSection] || hints['Mantelbogen'];
  }, [activeSection]);

  // ── Section fields ──

  const sectionFields = useMemo(() => {
    const fields: Record<string, Array<{ key: string; label: string; type: string }>> = {
      Mantelbogen: [
        { key: 'steuernummer', label: 'Steuernummer', type: 'text' },
        { key: 'steuer_id', label: 'Steuer-ID (11 digits)', type: 'text' },
        { key: 'full_name', label: 'Full name', type: 'text' },
        { key: 'address', label: 'Street, house no., postal code, city', type: 'text' },
        { key: 'iban', label: 'IBAN for refund', type: 'text' },
        { key: 'religion', label: 'Religious affiliation', type: 'text' },
      ],
      'Anlage N': [
        { key: 'bruttolohn', label: 'Gross salary (EUR)', type: 'number' },
        { key: 'lohnsteuer', label: 'Withheld wage tax (EUR)', type: 'number' },
        { key: 'soli', label: 'Solidarity surcharge withheld (EUR)', type: 'number' },
        { key: 'kirchensteuer', label: 'Church tax withheld (EUR)', type: 'number' },
        { key: 'commute_km', label: 'Commute distance (km)', type: 'number' },
        { key: 'commute_days', label: 'Commute days per year', type: 'number' },
        { key: 'home_office_days', label: 'Home office days', type: 'number' },
        { key: 'arbeitsmittel', label: 'Work equipment expenses (EUR)', type: 'number' },
        { key: 'fortbildung', label: 'Professional development (EUR)', type: 'number' },
        { key: 'kontofuehrung', label: 'Bank account fees (EUR, default 16)', type: 'number' },
        { key: 'gewerkschaft', label: 'Trade union dues (EUR)', type: 'number' },
      ],
      'Anlage V': [
        { key: 'mieteinnahmen', label: 'Annual rental income (EUR)', type: 'number' },
        { key: 'werbungskosten', label: 'Deductible expenses (EUR)', type: 'number' },
        { key: 'afa', label: 'Depreciation / AfA (EUR)', type: 'number' },
      ],
      'Anlage KAP': [
        { key: 'kapitalertraege', label: 'Capital gains (EUR)', type: 'number' },
        { key: 'abgeltungsteuer', label: 'Withheld capital gains tax (EUR)', type: 'number' },
        { key: 'freistellungsauftrag', label: 'Exemption order used (EUR)', type: 'number' },
      ],
      'Anlage Kind': [
        { key: 'child_name', label: 'Child name', type: 'text' },
        { key: 'child_dob', label: 'Date of birth', type: 'text' },
        { key: 'betreuungskosten', label: 'Childcare costs (EUR)', type: 'number' },
        { key: 'schulgeld', label: 'School fees (EUR)', type: 'number' },
      ],
      'Anlage Vorsorge': [
        { key: 'rentenversicherung', label: 'Pension insurance (EUR)', type: 'number' },
        { key: 'krankenversicherung', label: 'Health insurance (EUR)', type: 'number' },
        { key: 'pflegeversicherung', label: 'Long-term care insurance (EUR)', type: 'number' },
      ],
      'Anlage AUS': [
        { key: 'foreign_income', label: 'Foreign income (EUR)', type: 'number' },
        { key: 'foreign_tax_paid', label: 'Foreign tax paid (EUR)', type: 'number' },
      ],
    };
    return fields[activeSection] || [];
  }, [activeSection]);

  // ── Onboarding wizard steps ──

  const onboardingSteps = [
    {
      title: 'Personal information',
      content: (
        <div className="field-grid">
          <label>
            Bundesland
            <select value={profile.bundesland} onChange={(e) => setProfile({ ...profile, bundesland: e.target.value })}>
              {BUNDESLAENDER.map((b) => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </label>
          <label>
            Tax class (1-6)
            <input type="number" min={1} max={6} value={profile.tax_class}
              onChange={(e) => setProfile({ ...profile, tax_class: Number(e.target.value) })} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={profile.church_member}
              onChange={(e) => setProfile({ ...profile, church_member: e.target.checked })} />
            Church member (Kirchensteuer)
          </label>
        </div>
      ),
    },
    {
      title: 'Employment status',
      content: (
        <div className="field-grid">
          <label>
            Employment status
            <select value={profile.employment_status}
              onChange={(e) => setProfile({ ...profile, employment_status: e.target.value as OnboardingProfile['employment_status'] })}>
              <option value="employee">Employee</option>
              <option value="freelancer">Freelancer</option>
              <option value="both">Both (employed + freelance)</option>
              <option value="student">Student</option>
              <option value="unemployed">Unemployed</option>
              <option value="retired">Retired</option>
            </select>
          </label>
        </div>
      ),
    },
    {
      title: 'Income types',
      content: (
        <div className="field-grid">
          <label className="checkbox-row">
            <input type="checkbox" checked={profile.rental_income}
              onChange={(e) => setProfile({ ...profile, rental_income: e.target.checked })} />
            Rental income (Vermietung)
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={profile.capital_gains}
              onChange={(e) => setProfile({ ...profile, capital_gains: e.target.checked })} />
            Capital gains / investments
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={profile.foreign_income}
              onChange={(e) => setProfile({ ...profile, foreign_income: e.target.checked })} />
            Foreign income
          </label>
        </div>
      ),
    },
    {
      title: 'Family',
      content: (
        <div className="field-grid">
          <label>
            Marital status
            <select value={profile.marital_status}
              onChange={(e) => setProfile({ ...profile, marital_status: e.target.value as OnboardingProfile['marital_status'] })}>
              <option value="single">Single</option>
              <option value="married">Married</option>
            </select>
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={profile.has_children}
              onChange={(e) => setProfile({ ...profile, has_children: e.target.checked, num_children: e.target.checked ? Math.max(profile.num_children, 1) : 0 })} />
            Has children
          </label>
          {profile.has_children && (
            <label>
              Number of children
              <input type="number" min={1} max={20} value={profile.num_children}
                onChange={(e) => setProfile({ ...profile, num_children: Number(e.target.value) })} />
            </label>
          )}
        </div>
      ),
    },
    {
      title: 'Quick wins',
      content: (
        <div className="field-grid">
          <label>
            Home office days this year
            <input type="number" min={0} max={365} value={profile.home_office_days}
              onChange={(e) => setProfile({ ...profile, home_office_days: Number(e.target.value) })} />
          </label>
          <label>
            Commute distance (km, one way)
            <input type="number" min={0} max={1000} value={profile.commute_km}
              onChange={(e) => setProfile({ ...profile, commute_km: Number(e.target.value) })} />
          </label>
          <label>
            Working days per year
            <input type="number" min={0} max={365} value={profile.commute_days}
              onChange={(e) => setProfile({ ...profile, commute_days: Number(e.target.value) })} />
          </label>
          <label>
            Donations (EUR)
            <input type="number" min={0} step="0.01" value={profile.donations_eur}
              onChange={(e) => setProfile({ ...profile, donations_eur: Number(e.target.value) })} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={profile.has_haushaltsnahe}
              onChange={(e) => setProfile({ ...profile, has_haushaltsnahe: e.target.checked })} />
            Household services (cleaning, gardening, etc.)
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={profile.has_handwerker}
              onChange={(e) => setProfile({ ...profile, has_handwerker: e.target.checked })} />
            Craftsmen / repair services
          </label>
        </div>
      ),
    },
  ];

  // ═══════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════

  return (
    <main className="shell">
      {/* ── Language switch ── */}
      <div className="topbar">
        <div className="eyebrow">SteuerHelfer</div>
        <div className="lang-switch">
          <button type="button" className={`lang-button ${locale === 'de' ? 'is-active' : ''}`} onClick={() => setLocale('de')}>DE</button>
          <button type="button" className={`lang-button ${locale === 'en' ? 'is-active' : ''}`} onClick={() => setLocale('en')}>EN</button>
        </div>
      </div>

      {/* ── AUTH PAGE ── */}
      {page === 'auth' && (
        <section className="hero">
          <h1>{t.heroTitle}</h1>
          <p>{t.heroBody}</p>
          <div className="auth-form" style={{ marginTop: '24px', maxWidth: '400px' }}>
            <div className="step-switcher" style={{ marginBottom: '16px' }}>
              <button type="button" className={`step-button ${authMode === 'register' ? 'is-active' : ''}`} onClick={() => setAuthMode('register')}>Register</button>
              <button type="button" className={`step-button ${authMode === 'login' ? 'is-active' : ''}`} onClick={() => setAuthMode('login')}>Login</button>
            </div>
            <div className="field-grid">
              {authMode === 'register' && (
                <label>Full name <input type="text" value={authName} onChange={(e) => setAuthName(e.target.value)} /></label>
              )}
              <label>Email <input type="email" value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} /></label>
              <label>Password <input type="password" value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} /></label>
            </div>
            {authError && <p style={{ color: '#b91c1c', marginTop: '8px' }}>{authError}</p>}
            <button className="primary" type="button" style={{ marginTop: '16px' }} onClick={handleAuth}>
              {authMode === 'register' ? 'Create account' : 'Sign in'}
            </button>
          </div>
        </section>
      )}

      {/* ── NAV (post-auth) ── */}
      {page !== 'auth' && (
        <div className="step-switcher" style={{ margin: '18px 0' }}>
          {userName && <span style={{ marginRight: '12px', fontWeight: 600 }}>{userName}</span>}
          {(['onboarding', 'dashboard', 'taxform', 'documents', 'expenses', 'review', 'export', 'settings'] as Page[]).map((p) => (
            <button key={p} type="button" className={`step-button ${page === p ? 'is-active' : ''}`} onClick={() => setPage(p)}>
              {p === 'onboarding' ? t.onboarding : p === 'dashboard' ? t.dashboard : p === 'taxform' ? t.taxForm : p === 'documents' ? t.documents : p === 'expenses' ? 'Expenses' : p === 'review' ? t.review : p === 'export' ? t.export : 'Settings'}
            </button>
          ))}
        </div>
      )}

      {/* ── ONBOARDING WIZARD ── */}
      {page === 'onboarding' && (
        <section className="workspace-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <article className="panel">
            <div className="panel-heading">
              <h2>{onboardingSteps[onboardingStep].title}</h2>
              <span>Step {onboardingStep + 1} of {onboardingSteps.length}</span>
            </div>
            {onboardingSteps[onboardingStep].content}
            <div className="cta-row" style={{ marginTop: '20px' }}>
              {onboardingStep > 0 && (
                <button className="secondary" type="button" onClick={() => setOnboardingStep(onboardingStep - 1)}>Back</button>
              )}
              {onboardingStep < onboardingSteps.length - 1 ? (
                <button className="primary" type="button" onClick={() => setOnboardingStep(onboardingStep + 1)}>Next</button>
              ) : (
                <button className="primary" type="button" onClick={handleOnboardingSubmit}>Create tax return</button>
              )}
            </div>
          </article>
          <article className="panel">
            <div className="panel-heading"><h2>Preview</h2></div>
            <div className="metric-stack">
              <div><strong>Required Anlagen</strong><p>{requiredAnlagen.join(', ')}</p></div>
              <div><strong>Quick wins</strong></div>
            </div>
            <div className="suggestion-list">
              {quickWins.map((w) => (
                <div key={w} className="suggestion-item">{w}</div>
              ))}
            </div>
          </article>
        </section>
      )}

      {/* ── DASHBOARD ── */}
      {page === 'dashboard' && taxReturn && (
        <section className="panel-grid">
          <article className="panel">
            <div className="panel-heading">
              <h2>{t.dashboard}</h2>
              <span>{taxReturn.completion}% complete</span>
            </div>
            <div className="metric-stack">
              <div><strong>Tax year</strong><p>{taxReturn.tax_year}</p></div>
              <div><strong>Status</strong><p>{taxReturn.status}</p></div>
              <div><strong>Required Anlagen</strong><p>{taxReturn.required_anlagen.join(', ')}</p></div>
            </div>
            <div className="cta-row" style={{ marginTop: '16px' }}>
              <button className="primary" type="button" onClick={() => setPage('taxform')}>Fill tax forms</button>
              <button className="secondary" type="button" onClick={() => setPage('documents')}>Upload documents</button>
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading"><h2>Refund estimate</h2></div>
            <div className="field-grid">
              <label>
                Taxable income (EUR)
                <input type="number" min={0} value={estimateIncome} onChange={(e) => setEstimateIncome(Number(e.target.value))} />
              </label>
            </div>
            <div className="metric-stack" style={{ marginTop: '14px' }}>
              <div><strong>{estimate.incomeTax.toLocaleString()} EUR</strong><p>Income tax</p></div>
              <div><strong>{estimate.solidaritySurcharge.toLocaleString()} EUR</strong><p>Solidarity surcharge</p></div>
              <div><strong>{estimate.churchTax.toLocaleString()} EUR</strong><p>Church tax</p></div>
              <div><strong>{estimate.totalTax.toLocaleString()} EUR</strong><p>Total tax ({estimate.effectiveRate}% effective rate)</p></div>
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading"><h2>Quick wins</h2></div>
            <div className="suggestion-list">
              {quickWins.map((w) => (
                <div key={w} className="suggestion-item">{w}</div>
              ))}
            </div>
          </article>
        </section>
      )}

      {/* ── TAX FORM ── */}
      {page === 'taxform' && taxReturn && (
        <section className="workspace-grid">
          <article className="panel form-panel">
            <div className="panel-heading">
              <h2>{t.taxForm}: {activeSection}</h2>
              <span>{saveStatus}</span>
            </div>
            <div className="section-switcher">
              {taxReturn.required_anlagen.map((section) => (
                <button key={section} type="button"
                  className={`section-button ${activeSection === section ? 'is-active' : ''}`}
                  onClick={() => { setActiveSection(section); setSectionValues({}); setSaveStatus(''); }}>
                  {section}
                </button>
              ))}
            </div>
            <div className="field-grid" style={{ marginTop: '16px' }}>
              {sectionFields.map((field) => (
                <label key={field.key}>
                  {field.label}
                  <input
                    type={field.type}
                    value={sectionValues[field.key] ?? ''}
                    onChange={(e) => setSectionValues({ ...sectionValues, [field.key]: e.target.value })}
                  />
                </label>
              ))}
            </div>
            <button className="primary" type="button" style={{ marginTop: '16px' }} onClick={handleSaveSection}>
              Save section
            </button>
          </article>

          <article className="panel summary-panel">
            <div className="panel-heading"><h2>Section data</h2></div>
            <div className="suggestion-list">
              {Object.entries(sectionValues).filter(([, v]) => v).map(([k, v]) => (
                <div key={k} className="suggestion-item"><strong>{k}:</strong> {v}</div>
              ))}
              {Object.entries(sectionValues).filter(([, v]) => v).length === 0 && (
                <div className="suggestion-item">Fill in the fields on the left to see a summary here.</div>
              )}
            </div>
          </article>

          <ElsterFieldHint {...sectionHint} />
        </section>
      )}

      {/* ── DOCUMENTS ── */}
      {page === 'documents' && (
        <section className="panel-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <article className="panel">
            <div className="panel-heading">
              <h2>{t.documents}</h2>
              <span>{t.uploadLabel}</span>
            </div>
            <p style={{ marginBottom: '12px', color: 'rgba(29,27,22,0.7)' }}>
              Upload your tax documents — Lohnsteuerbescheinigung, receipts, insurance certificates, rental documents, donation receipts, broker statements, etc.
            </p>
            <div style={{ border: '2px dashed rgba(29,27,22,0.2)', borderRadius: '12px', padding: '32px', textAlign: 'center', background: 'rgba(255,255,255,0.4)' }}>
              <div style={{ fontSize: '2rem', marginBottom: '8px' }}>+</div>
              <p style={{ marginBottom: '12px' }}>Drag files here or click to browse</p>
              <input
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png,.tiff,.bmp,.doc,.docx,.xls,.xlsx"
                style={{ margin: '0 auto' }}
                onChange={handleUploadDocument}
              />
            </div>
            {uploadStatus && <p style={{ marginTop: '8px', color: uploadStatus.includes('Failed') ? '#b91c1c' : '#166534' }}>{uploadStatus}</p>}
          </article>

          <article className="panel">
            <div className="panel-heading">
              <h2>Uploaded documents</h2>
              <span>{uploadedDocs.length} file(s)</span>
            </div>
            {uploadedDocs.length === 0 && <p>No documents uploaded yet. Upload your Lohnsteuerbescheinigung, receipts, and other tax documents.</p>}
            <div className="suggestion-list">
              {uploadedDocs.map((doc) => (
                <div key={doc.document_id} className="suggestion-item">
                  <strong>{doc.file_name}</strong> — {doc.classification} ({(doc.confidence * 100).toFixed(0)}% confidence)
                  <div style={{ marginTop: '6px', fontSize: '0.9rem', color: 'rgba(29,27,22,0.65)' }}>
                    {Object.entries(doc.extracted_fields).map(([k, v]) => `${k}: ${v}`).join(' · ')}
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>
      )}

      {/* ── EXPENSES ── */}
      {page === 'expenses' && taxReturn && (
        <section className="panel-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <article className="panel">
            <div className="panel-heading">
              <h2>Add expense / receipt</h2>
              <span>Track deductible costs</span>
            </div>
            <p style={{ marginBottom: '12px', color: 'rgba(29,27,22,0.7)' }}>
              Add every deductible expense — work tools, training, travel, insurance, medical, and more. Each one maps to a specific ELSTER form and line.
            </p>
            <div className="field-grid">
              <label>
                Category
                <select value={newExpenseCategory} onChange={(e) => setNewExpenseCategory(e.target.value)}>
                  {Object.keys(expenseCategories).length > 0
                    ? Object.entries(expenseCategories).map(([key, cat]) => (
                        <option key={key} value={key}>{cat.label_de} — {cat.label_en}</option>
                      ))
                    : <>
                        <option value="work_equipment">Arbeitsmittel — Work equipment</option>
                        <option value="training">Fortbildungskosten — Training</option>
                        <option value="software">Software und Lizenzen — Software</option>
                        <option value="phone_internet">Telefon und Internet — Phone/Internet</option>
                        <option value="professional_books">Fachliteratur — Books</option>
                        <option value="work_clothing">Berufskleidung — Work clothing</option>
                        <option value="job_search">Bewerbungskosten — Job search</option>
                        <option value="business_travel">Reisekosten — Travel</option>
                        <option value="donations">Spenden — Donations</option>
                        <option value="medical">Krankheitskosten — Medical</option>
                        <option value="misc_werbungskosten">Sonstige — Other work expenses</option>
                      </>
                  }
                </select>
              </label>
              {expenseCategories[newExpenseCategory]?.hint && (
                <div style={{ fontSize: '0.85rem', color: 'rgba(29,27,22,0.6)', padding: '6px 10px', background: 'rgba(255,255,255,0.5)', borderRadius: '8px' }}>
                  {expenseCategories[newExpenseCategory].hint}
                  <br />
                  <strong>{expenseCategories[newExpenseCategory].form}, {expenseCategories[newExpenseCategory].line}</strong>
                </div>
              )}
              <label>
                Description
                <input type="text" placeholder="e.g. Laptop for work, German course, train ticket" value={newExpenseDesc} onChange={(e) => setNewExpenseDesc(e.target.value)} />
              </label>
              <label>
                Amount (EUR)
                <input type="number" min="0.01" step="0.01" placeholder="0.00" value={newExpenseAmount} onChange={(e) => setNewExpenseAmount(e.target.value)} />
              </label>
              <label>
                Date
                <input type="date" value={newExpenseDate} onChange={(e) => setNewExpenseDate(e.target.value)} />
              </label>
            </div>
            {expenseStatus && <p style={{ marginTop: '8px', color: expenseStatus === 'Added' ? '#166534' : 'rgba(29,27,22,0.7)' }}>{expenseStatus}</p>}
            <button className="primary" type="button" style={{ marginTop: '14px' }} onClick={handleAddExpense}>
              Add expense
            </button>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <h2>Totals by category</h2>
              <span>{expenseGrandTotal.toLocaleString('de-DE', { minimumFractionDigits: 2 })} EUR total</span>
            </div>
            {Object.keys(expenseTotals).length === 0 && <p>No expenses added yet. Start tracking your deductible costs to maximize your tax refund.</p>}
            <div className="metric-stack">
              {Object.entries(expenseTotals).map(([cat, total]) => (
                <div key={cat}>
                  <strong>{total.toLocaleString('de-DE', { minimumFractionDigits: 2 })} EUR</strong>
                  <p>{expenseCategories[cat]?.label_de || cat} — {expenseCategories[cat]?.form}, {expenseCategories[cat]?.line}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="panel" style={{ gridColumn: '1 / -1' }}>
            <div className="panel-heading">
              <h2>All expenses</h2>
              <span>{expenses.length} item(s)</span>
            </div>
            {expenses.length === 0 && <p>No expenses yet.</p>}
            <div className="suggestion-list">
              {expenses.map((exp) => (
                <div key={exp.expense_id} className="suggestion-item" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <strong>{exp.description}</strong> — {exp.amount_eur.toLocaleString('de-DE', { minimumFractionDigits: 2 })} EUR
                    <div style={{ marginTop: '4px', fontSize: '0.85rem', color: 'rgba(29,27,22,0.6)' }}>
                      {exp.category_label} · {exp.date} · {exp.form}, {exp.line}
                    </div>
                  </div>
                  <button type="button" style={{ background: 'none', border: 'none', color: '#b91c1c', cursor: 'pointer', fontSize: '1.1rem', padding: '4px 8px' }}
                    onClick={() => handleDeleteExpense(exp.expense_id)}>
                    X
                  </button>
                </div>
              ))}
            </div>
          </article>
        </section>
      )}

      {/* ── REVIEW ── */}
      {page === 'review' && (
        <section className="panel-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <article className="panel">
            <div className="panel-heading">
              <h2>{t.review}</h2>
              <span>AI deduction optimizer</span>
            </div>
            {suggestions.length === 0 && <p>Loading suggestions...</p>}
            <div className="suggestion-list">
              {suggestions.map((s) => (
                <div key={s.field_id} className="suggestion-item">
                  <strong>{s.title}</strong>
                  {s.amount_eur !== null && <span> — {s.amount_eur.toLocaleString()} EUR</span>}
                  <div style={{ marginTop: '4px', fontSize: '0.9rem', color: 'rgba(29,27,22,0.65)' }}>
                    {s.form}, {s.line} — {s.reason}
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading"><h2>Refund estimate</h2></div>
            <div className="metric-stack">
              <div><strong>{estimate.totalTax.toLocaleString()} EUR</strong><p>Estimated total tax</p></div>
              <div><strong>{estimate.effectiveRate}%</strong><p>Effective tax rate</p></div>
              <div><strong>{profile.marital_status === 'married' ? 'Joint' : 'Single'}</strong><p>Filing type{profile.marital_status === 'married' ? ' (Splittingverfahren)' : ''}</p></div>
            </div>
          </article>
        </section>
      )}

      {/* ── SETTINGS ── */}
      {page === 'settings' && (
        <section className="panel-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <article className="panel">
            <div className="panel-heading">
              <h2>LLM API key</h2>
              <span>Bring your own key</span>
            </div>
            <p style={{ marginBottom: '14px', color: 'rgba(29,27,22,0.7)' }}>
              Connect any LLM provider to power document analysis and deduction suggestions.
            </p>
            <div className="field-grid">
              <label>
                Provider
                <select value={llmProvider} onChange={(e) => { setLlmProvider(e.target.value); setLlmModel(''); }}>
                  {Object.keys(llmProviders).length > 0
                    ? Object.entries(llmProviders).map(([key, info]) => (
                        <option key={key} value={key}>{info.name}</option>
                      ))
                    : <>
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Anthropic</option>
                        <option value="google">Google Gemini</option>
                        <option value="mistral">Mistral AI</option>
                        <option value="cohere">Cohere</option>
                        <option value="custom">Custom / Self-hosted</option>
                      </>
                  }
                </select>
              </label>
              <label>
                Model
                {llmProviders[llmProvider]?.models?.length ? (
                  <select value={llmModel || llmProviders[llmProvider]?.default_model || ''} onChange={(e) => setLlmModel(e.target.value)}>
                    {llmProviders[llmProvider].models.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                ) : (
                  <input type="text" placeholder="e.g. gpt-4o, claude-sonnet-5" value={llmModel} onChange={(e) => setLlmModel(e.target.value)} />
                )}
              </label>
              <label>
                API key
                <input type="password" placeholder="sk-... or your provider's key" value={llmApiKey} onChange={(e) => setLlmApiKey(e.target.value)} />
              </label>
            </div>
            {llmStatus && <p style={{ marginTop: '8px', color: llmStatus.startsWith('Saved') ? '#166534' : 'rgba(29,27,22,0.7)' }}>{llmStatus}</p>}
            <div className="cta-row" style={{ marginTop: '16px' }}>
              <button className="primary" type="button" onClick={handleSaveLlm}>Save API key</button>
              {llmConfigured && (
                <button className="secondary" type="button" onClick={handleDeleteLlm}>Remove key</button>
              )}
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading"><h2>Current configuration</h2></div>
            {llmConfigured ? (
              <div className="metric-stack">
                <div><strong>Provider</strong><p>{llmProviders[llmProvider]?.name || llmProvider}</p></div>
                <div><strong>Model</strong><p>{llmModel || llmProviders[llmProvider]?.default_model || 'default'}</p></div>
                <div><strong>API key</strong><p>{llmKeyPreview}</p></div>
                <div><strong>Status</strong><p>Active</p></div>
              </div>
            ) : (
              <div className="metric-stack">
                <div><strong>Not configured</strong><p>Enter your API key to enable AI-powered document analysis, smart extraction, and deduction suggestions.</p></div>
              </div>
            )}
            <div className="suggestion-list" style={{ marginTop: '16px' }}>
              <div className="suggestion-item">Your API key is stored server-side for your session only and never shared.</div>
              <div className="suggestion-item">The key is used for: document classification, field extraction, and deduction optimization.</div>
              <div className="suggestion-item">Typical cost: ~0.05-0.15 EUR per document processed.</div>
            </div>
          </article>
        </section>
      )}

      {/* ── EXPORT ── */}
      {page === 'export' && taxReturn && (
        <section className="panel-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <article className="panel">
            <div className="panel-heading">
              <h2>{t.export}</h2>
              <span>PDF / CSV</span>
            </div>
            <p>Download your tax return data with ELSTER form and line mappings.</p>
            <div className="export-actions" style={{ marginTop: '16px' }}>
              <a className="primary" style={{ display: 'inline-block', padding: '14px 18px', borderRadius: '999px', textDecoration: 'none', fontWeight: 600, color: '#fff7e8', background: '#1d1b16' }}
                href={api.exportPdfUrl(taxReturn.tax_return_id)} target="_blank" rel="noopener noreferrer">
                {t.exportPdf}
              </a>
              <a className="secondary" style={{ display: 'inline-block', padding: '14px 18px', borderRadius: '999px', textDecoration: 'none', fontWeight: 600, color: '#1d1b16', background: 'rgba(255,255,255,0.72)', border: '1px solid rgba(29,27,22,0.12)' }}
                href={api.exportCsv(taxReturn.tax_return_id)} target="_blank" rel="noopener noreferrer">
                {t.exportCsv}
              </a>
            </div>
          </article>

          <article className="panel">
            <div className="panel-heading"><h2>Completion</h2></div>
            <div className="metric-stack">
              <div><strong>{taxReturn.completion}%</strong><p>Sections completed</p></div>
              <div><strong>{Object.keys(taxReturn.sections).length} / {taxReturn.required_anlagen.length}</strong><p>Anlagen filled</p></div>
              <div><strong>{taxReturn.status}</strong><p>Current status</p></div>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
