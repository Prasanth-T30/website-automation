import Tesseract from "tesseract.js";

const normalizeText = (text) => text.replace(/\s+/g, " ").trim();

const parseAmount = (value) => {
  const num = parseFloat(String(value ?? "").replace(/[^0-9.]/g, ""));
  return Number.isNaN(num) ? null : num;
};

// Extracts every number-like token from OCR text (handles "500", "500.00", "1,234", "Rs.500", "₹500").
const extractNumbers = (text) => {
  const matches = text.match(/\d[\d,]*(?:\.\d{1,2})?/g) || [];
  return matches.map((m) => parseFloat(m.replace(/,/g, ""))).filter((n) => !Number.isNaN(n));
};

// Phrases commonly seen on payment-success screenshots — deliberately generic
// (not tied to one app's exact wording) so it works across PhonePe, Google Pay,
// BHIM, Paytm, Amazon Pay, and most bank/UPI apps.
const PAYMENT_KEYWORDS = [
  "paid to",
  "paid from",
  "payment successful",
  "transaction successful",
  "transaction id",
  "upi transaction id",
  "upi ref",
  "reference no",
  "successful",
  "transaction",
  "amount",
  "upi",
];

// App name is optional — used only as a bonus signal, never required.
const APP_NAME_KEYWORDS = ["phonepe", "google pay", "gpay", "bhim", "paytm", "amazon pay"];

const countMatches = (text, keywords) => keywords.filter((kw) => text.includes(kw)).length;

// Heuristic check for "does this look like a real UPI payment screenshot at all"
// (has an amount, a long ID-like number, and a couple of payment-related phrases).
const looksLikePaymentScreenshot = (normalizedLowerText, numbersFound) => {
  const keywordHits = countMatches(normalizedLowerText, PAYMENT_KEYWORDS);
  const hasLongId = numbersFound.some((n) => String(Math.trunc(n)).length >= 6);
  const hasAmount = numbersFound.length > 0;
  return keywordHits >= 2 && hasLongId && hasAmount;
};

/**
 * Runs OCR on the payment screenshot (via Tesseract.js — free, fully
 * client-side, no API keys or paid services) and checks it against three
 * signals:
 *   1. formatValid    — does the image actually look like a UPI payment screenshot?
 *   2. amountMatch     — does the typed "Amount Paid" appear in the screenshot?
 *   3. transactionMatch — does the typed "UPI Transaction ID" appear in the screenshot?
 *
 * The registration is accepted when at least two of these three checks pass,
 * so a single OCR misread (e.g. a slightly blurry digit) doesn't block a
 * genuine payment. It works the same way regardless of which app the
 * screenshot came from (PhonePe, Google Pay, BHIM, Paytm, Amazon Pay, etc.)
 * since none of the checks depend on a specific app's layout.
 */
export async function verifyPaymentScreenshot(file, amount, transactionId) {
  if (!file) {
    return { isValid: false, passCount: 0, formatValid: false, amountMatch: false, transactionMatch: false, reason: "No screenshot provided" };
  }

  let text = "";
  try {
    const result = await Tesseract.recognize(file, "eng");
    text = result?.data?.text || "";
  } catch (err) {
    return { isValid: false, passCount: 0, formatValid: false, amountMatch: false, transactionMatch: false, reason: "Could not read the screenshot" };
  }

  const normalized = normalizeText(text);
  const normalizedLower = normalized.toLowerCase();
  const numbersFound = extractNumbers(normalized);
  const targetAmount = parseAmount(amount);

  const formatValid = looksLikePaymentScreenshot(normalizedLower, numbersFound);
  const amountMatch = targetAmount !== null && numbersFound.some((n) => Math.abs(n - targetAmount) < 0.01);

  const cleanedTransactionId = String(transactionId || "").replace(/[\s-]/g, "").toLowerCase();
  const cleanedText = normalizedLower.replace(/[\s-]/g, "");
  const transactionMatch = cleanedTransactionId.length >= 4 && cleanedText.includes(cleanedTransactionId);

  const appDetected = APP_NAME_KEYWORDS.find((kw) => normalizedLower.includes(kw)) || null;
  const passCount = [formatValid, amountMatch, transactionMatch].filter(Boolean).length;

  return {
    isValid: passCount >= 2,
    passCount,
    formatValid,
    amountMatch,
    transactionMatch,
    appDetected,
    extractedText: text,
  };
}
