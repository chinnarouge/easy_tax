export type TaxEstimateInput = {
  taxableIncome: number;
  filingType: 'single' | 'joint';
  churchTaxRate: number;
};

export type TaxEstimateResult = {
  incomeTax: number;
  solidaritySurcharge: number;
  churchTax: number;
  totalTax: number;
  effectiveRate: number;
};

function computeIncomeTax(taxableIncome: number): number {
  if (taxableIncome <= 0) return 0;
  if (taxableIncome <= 12096) return 0;
  if (taxableIncome <= 17443) {
    const y = (taxableIncome - 12096) / 10000;
    return (922.98 * y + 1400) * y;
  }
  if (taxableIncome <= 68480) {
    const z = (taxableIncome - 17443) / 10000;
    return (181.19 * z + 2397) * z + 1016.37;
  }
  if (taxableIncome <= 277825) {
    return 0.42 * taxableIncome - 10693.32;
  }
  return 0.45 * taxableIncome - 18956.63;
}

function computeSoli(incomeTax: number): number {
  if (incomeTax <= 18130) return 0;
  if (incomeTax <= 33100) return (incomeTax - 18130) * 0.119;
  return incomeTax * 0.055;
}

export function estimateTax(input: TaxEstimateInput): TaxEstimateResult {
  let incomeTax: number;
  if (input.filingType === 'joint') {
    incomeTax = computeIncomeTax(input.taxableIncome / 2) * 2;
  } else {
    incomeTax = computeIncomeTax(input.taxableIncome);
  }

  const solidaritySurcharge = computeSoli(incomeTax);
  const churchTax = incomeTax * input.churchTaxRate;
  const totalTax = incomeTax + solidaritySurcharge + churchTax;
  const effectiveRate = input.taxableIncome > 0 ? (totalTax / input.taxableIncome) * 100 : 0;

  return {
    incomeTax: Number(incomeTax.toFixed(2)),
    solidaritySurcharge: Number(solidaritySurcharge.toFixed(2)),
    churchTax: Number(churchTax.toFixed(2)),
    totalTax: Number(totalTax.toFixed(2)),
    effectiveRate: Number(effectiveRate.toFixed(2)),
  };
}
