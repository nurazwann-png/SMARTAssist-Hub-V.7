/* ═══════════════════════════════════════
   SMARTAssist Hub — SPA Controller
   ═══════════════════════════════════════ */

// ── State ──
let currentAgent = null;
let sessionId = null;
let isProcessing = false;
let chartCounter = 0;
let hasUploadedData = false;
let lastActiveAgent = 'fallback';
let lastStructuredData = null;
let currentLang = localStorage.getItem('smartassist_lang') || 'bm';
let _msgIndex = 0;

// ── i18n ──
const I18N = {
    bm: {
        nav_home: 'UTAMA', nav_agents: 'EJEN',
        hero_subtitle: 'Selamat Datang',
        agent_data_name: 'Analisis Data', agent_data_desc: 'Analisis fail CSV/Excel, jana carta dan statistik',
        agent_report_name: 'Jana Laporan', agent_report_desc: 'Jana laporan satu muka surat format rasmi KPM',
        agent_letter_name: 'Tulis Surat Rasmi', agent_letter_desc: 'Jana surat rasmi, memo dan surat siaran KPM',
        agent_reviewer_name: 'Semak Dokumen', agent_reviewer_desc: 'Semak tatabahasa, format dan pematuhan dokumen',
        agent_kpm_name: 'Sokongan KPM', agent_kpm_desc: 'Bantuan sistem EMIS, APDM, DTP dan polisi KPM',
        history_title: 'Sejarah Sesi', history_empty: 'Tiada sejarah sesi lagi.',
        input_placeholder: 'Taip mesej anda di sini...',
        back_btn: '← Kembali', new_session: 'Sesi Baharu',
        lh_title: 'Kepala Surat & Logo',
        lh_tab_letter: 'Kepala Surat (Surat Rasmi)',
        lh_tab_logo: 'Logo (Laporan)',
        lh_upload_label: 'Klik atau seret fail imej ke sini',
        lh_upload_hint: 'PNG, JPG, GIF, WEBP — maks 5 MB setiap fail',
        lh_upload_btn: 'Pilih Fail',
        lh_empty: 'Tiada imej dimuat naik lagi.',
        lh_active_label: 'Aktif',
        lh_select: 'Gunakan', lh_selected: 'Digunakan',
        lh_delete: '🗑', lh_upload_success: 'Imej berjaya dimuat naik.',
        lh_upload_fail: 'Gagal muat naik fail.',
        word_preview: 'Pratonton Dokumen', word_close: 'Tutup',
    },
    en: {
        nav_home: 'HOME', nav_agents: 'AGENTS',
        hero_subtitle: 'Welcome',
        agent_data_name: 'Data Analysis', agent_data_desc: 'Analyse CSV/Excel files, generate charts and statistics',
        agent_report_name: 'Report Generator', agent_report_desc: 'Generate one-page reports in official KPM format',
        agent_letter_name: 'Official Letter', agent_letter_desc: 'Draft official letters, memos and circulars',
        agent_reviewer_name: 'Document Review', agent_reviewer_desc: 'Check grammar, format and document compliance',
        agent_kpm_name: 'KPM Support', agent_kpm_desc: 'Help with EMIS, APDM, DTP systems and KPM policies',
        history_title: 'Session History', history_empty: 'No session history yet.',
        input_placeholder: 'Type your message here...',
        back_btn: '← Back', new_session: 'New Session',
        lh_title: 'Letterhead & Logo',
        lh_tab_letter: 'Letterhead (Official Letters)',
        lh_tab_logo: 'Logo (Reports)',
        lh_upload_label: 'Click or drag image files here',
        lh_upload_hint: 'PNG, JPG, GIF, WEBP — max 5 MB each',
        lh_upload_btn: 'Choose File',
        lh_empty: 'No images uploaded yet.',
        lh_active_label: 'Active',
        lh_select: 'Use', lh_selected: 'In Use',
        lh_delete: '🗑', lh_upload_success: 'Image uploaded successfully.',
        lh_upload_fail: 'Failed to upload file.',
        word_preview: 'Document Preview', word_close: 'Close',
    },
};

function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('smartassist_lang', lang);
    const dict = I18N[lang];
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) el.textContent = dict[key];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (dict[key]) el.placeholder = dict[key];
    });
    const toggle = document.getElementById('langToggle');
    if (toggle) {
        toggle.querySelector('.lang-flag').textContent = lang === 'bm' ? '🇲🇾' : '🇬🇧';
        toggle.querySelector('.lang-code').textContent = lang === 'bm' ? 'BM' : 'EN';
    }
    document.getElementById('backBtn').textContent = dict.back_btn;
}

function toggleLanguage() {
    applyLanguage(currentLang === 'bm' ? 'en' : 'bm');
}

// ── DOM refs ──
const landingPage = document.getElementById('landingPage');
const agentCanvas = document.getElementById('agentCanvas');
const historyPanel = document.getElementById('historyPanel');
const historyOverlay = document.getElementById('historyOverlay');
const historyList = document.getElementById('historyList');

const canvasMessages = document.getElementById('canvasMessages');
const canvasWelcome = document.getElementById('canvasWelcome');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const fileIndicator = document.getElementById('fileIndicator');
const fileIndicatorText = document.getElementById('fileIndicatorText');
const fileRemoveBtn = document.getElementById('fileRemoveBtn');
const typingIndicator = document.getElementById('typingIndicator');

const AGENT_ICONS = {
    data_analysis: `<svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="hbg-d" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#3b1f6e"/><stop offset="70%" stop-color="#1a0b3b"/><stop offset="100%" stop-color="#0a061a"/></radialGradient><radialGradient id="hinn-d" cx="50%" cy="40%" r="50%"><stop offset="0%" stop-color="#7c3aed" stop-opacity="0.35"/><stop offset="100%" stop-color="transparent"/></radialGradient><filter id="hgw-d"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><circle cx="40" cy="40" r="38" fill="url(#hbg-d)"/><circle cx="40" cy="40" r="38" fill="url(#hinn-d)"/><circle cx="40" cy="40" r="36.5" stroke="#9333ea" stroke-width="1" opacity="0.4" filter="url(#hgw-d)"/><circle cx="40" cy="40" r="37.5" stroke="#c084fc" stroke-width="1.5" opacity="0.85" filter="url(#hgw-d)"/><circle cx="40" cy="40" r="33" stroke="#7c3aed" stroke-width="0.6" stroke-dasharray="3 4" opacity="0.5"/><path d="M28 36 C24 33 23 28 26 25 C27 22 30 21 33 22 C33 19 36 17 39 18 C39 17 40 17 40 18" stroke="#c084fc" stroke-width="1.8" stroke-linecap="round" fill="none" filter="url(#hgw-d)"/><path d="M28 36 C25 38 25 42 28 44 C27 47 29 50 32 49 C32 51 34 52 36 51 C37 53 40 52 40 50" stroke="#c084fc" stroke-width="1.8" stroke-linecap="round" fill="none" filter="url(#hgw-d)"/><path d="M52 36 C56 33 57 28 54 25 C53 22 50 21 47 22 C47 19 44 17 41 18 C41 17 40 17 40 18" stroke="#a78bfa" stroke-width="1.8" stroke-linecap="round" fill="none" filter="url(#hgw-d)"/><path d="M52 36 C55 38 55 42 52 44 C53 47 51 50 48 49 C48 51 46 52 44 51 C43 53 40 52 40 50" stroke="#a78bfa" stroke-width="1.8" stroke-linecap="round" fill="none" filter="url(#hgw-d)"/><line x1="40" y1="18" x2="40" y2="50" stroke="#ddd6fe" stroke-width="1" stroke-dasharray="2 3" opacity="0.6"/><circle cx="33" cy="30" r="2" fill="#c084fc" filter="url(#hgw-d)"/><circle cx="47" cy="30" r="2" fill="#a78bfa" filter="url(#hgw-d)"/><circle cx="30" cy="40" r="1.5" fill="#c084fc" filter="url(#hgw-d)"/><circle cx="50" cy="40" r="1.5" fill="#a78bfa" filter="url(#hgw-d)"/><line x1="33" y1="32" x2="22" y2="56" stroke="#7c3aed" stroke-width="0.8" opacity="0.5"/><line x1="40" y1="50" x2="40" y2="58" stroke="#7c3aed" stroke-width="0.8" opacity="0.5"/><line x1="47" y1="32" x2="58" y2="56" stroke="#7c3aed" stroke-width="0.8" opacity="0.5"/><rect x="18" y="58" width="5" height="8" rx="1" fill="#7c3aed" opacity="0.7" filter="url(#hgw-d)"/><rect x="25" y="53" width="5" height="13" rx="1" fill="#9333ea" opacity="0.85" filter="url(#hgw-d)"/><rect x="32" y="55" width="5" height="11" rx="1" fill="#7c3aed" opacity="0.7" filter="url(#hgw-d)"/><rect x="39" y="50" width="5" height="16" rx="1" fill="#c084fc" filter="url(#hgw-d)"/><rect x="46" y="52" width="5" height="14" rx="1" fill="#9333ea" opacity="0.85" filter="url(#hgw-d)"/><rect x="53" y="57" width="5" height="9" rx="1" fill="#7c3aed" opacity="0.7" filter="url(#hgw-d)"/></svg>`,
    letter_generator: `<svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="hbg-l" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#3b2506"/><stop offset="70%" stop-color="#1c1003"/><stop offset="100%" stop-color="#0a0601"/></radialGradient><radialGradient id="hinn-l" cx="50%" cy="40%" r="50%"><stop offset="0%" stop-color="#d97706" stop-opacity="0.3"/><stop offset="100%" stop-color="transparent"/></radialGradient><filter id="hgw-l"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><circle cx="40" cy="40" r="38" fill="url(#hbg-l)"/><circle cx="40" cy="40" r="38" fill="url(#hinn-l)"/><circle cx="40" cy="40" r="36.5" stroke="#b45309" stroke-width="1" opacity="0.4" filter="url(#hgw-l)"/><circle cx="40" cy="40" r="37.5" stroke="#fbbf24" stroke-width="1.5" opacity="0.85" filter="url(#hgw-l)"/><circle cx="40" cy="40" r="33" stroke="#d97706" stroke-width="0.6" stroke-dasharray="3 4" opacity="0.5"/><rect x="18" y="12" width="32" height="42" rx="2.5" fill="#1c1003" stroke="#fbbf24" stroke-width="1.5" opacity="0.9"/><rect x="18" y="12" width="32" height="9" rx="2" fill="#78350f" opacity="0.85"/><line x1="22" y1="16" x2="46" y2="16" stroke="#fcd34d" stroke-width="1" opacity="0.7"/><line x1="22" y1="19" x2="38" y2="19" stroke="#fcd34d" stroke-width="0.8" opacity="0.5"/><line x1="23" y1="27" x2="46" y2="27" stroke="#fbbf24" stroke-width="1.1" stroke-linecap="round" opacity="0.5"/><line x1="23" y1="31" x2="46" y2="31" stroke="#fbbf24" stroke-width="1.1" stroke-linecap="round" opacity="0.5"/><line x1="23" y1="35" x2="46" y2="35" stroke="#fbbf24" stroke-width="1.1" stroke-linecap="round" opacity="0.4"/><line x1="23" y1="39" x2="36" y2="39" stroke="#fbbf24" stroke-width="1.1" stroke-linecap="round" opacity="0.35"/><line x1="23" y1="49" x2="40" y2="49" stroke="#f59e0b" stroke-width="0.9" opacity="0.6"/><path d="M24 47 Q27 44 30 47 Q33 50 36 47" stroke="#fcd34d" stroke-width="1.2" fill="none" stroke-linecap="round" filter="url(#hgw-l)"/><rect x="43" y="26" width="7" height="28" rx="3" transform="rotate(-35 43 26)" fill="#92400e" stroke="#fbbf24" stroke-width="1.2"/><polygon points="34,58 38,54 40,60" fill="#fbbf24" filter="url(#hgw-l)"/><rect x="43" y="26" width="7" height="7" rx="2" transform="rotate(-35 43 26)" fill="#fbbf24" opacity="0.9"/></svg>`,
    report_generator: `<svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="hbg-r" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#0f3320"/><stop offset="70%" stop-color="#071a0f"/><stop offset="100%" stop-color="#020a04"/></radialGradient><radialGradient id="hinn-r" cx="50%" cy="40%" r="50%"><stop offset="0%" stop-color="#16a34a" stop-opacity="0.3"/><stop offset="100%" stop-color="transparent"/></radialGradient><filter id="hgw-r"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><circle cx="40" cy="40" r="38" fill="url(#hbg-r)"/><circle cx="40" cy="40" r="38" fill="url(#hinn-r)"/><circle cx="40" cy="40" r="36.5" stroke="#15803d" stroke-width="1" opacity="0.4" filter="url(#hgw-r)"/><circle cx="40" cy="40" r="37.5" stroke="#4ade80" stroke-width="1.5" opacity="0.85" filter="url(#hgw-r)"/><circle cx="40" cy="40" r="33" stroke="#16a34a" stroke-width="0.6" stroke-dasharray="3 4" opacity="0.5"/><rect x="20" y="13" width="30" height="40" rx="2.5" fill="#0d2b18" stroke="#4ade80" stroke-width="1.5" opacity="0.9"/><path d="M44 13 L50 19 L44 19 Z" fill="#166534" stroke="#4ade80" stroke-width="1" stroke-linejoin="round"/><rect x="20" y="13" width="24" height="7" rx="2" fill="#166534" opacity="0.8"/><text x="32" y="19" text-anchor="middle" font-size="5" font-family="Arial" font-weight="bold" fill="#86efac">REPORT</text><line x1="25" y1="27" x2="45" y2="27" stroke="#4ade80" stroke-width="1.2" stroke-linecap="round" opacity="0.5"/><line x1="25" y1="31" x2="45" y2="31" stroke="#4ade80" stroke-width="1.2" stroke-linecap="round" opacity="0.5"/><line x1="25" y1="35" x2="38" y2="35" stroke="#4ade80" stroke-width="1.2" stroke-linecap="round" opacity="0.4"/><polyline points="24,47 29,43 34,45 40,38 46,40" stroke="#22c55e" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none" filter="url(#hgw-r)"/><polygon points="46,40 50,34 44,36" fill="#22c55e" filter="url(#hgw-r)"/><rect x="54" y="44" width="5" height="9" rx="1" fill="#16a34a" opacity="0.8" filter="url(#hgw-r)"/><rect x="61" y="39" width="5" height="14" rx="1" fill="#4ade80" opacity="0.9" filter="url(#hgw-r)"/><rect x="68" y="42" width="5" height="11" rx="1" fill="#16a34a" opacity="0.8" filter="url(#hgw-r)"/></svg>`,
    document_reviewer: `<svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="hbg-c" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#082d40"/><stop offset="70%" stop-color="#041620"/><stop offset="100%" stop-color="#01080f"/></radialGradient><radialGradient id="hinn-c" cx="50%" cy="40%" r="50%"><stop offset="0%" stop-color="#0891b2" stop-opacity="0.3"/><stop offset="100%" stop-color="transparent"/></radialGradient><filter id="hgw-c"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><circle cx="40" cy="40" r="38" fill="url(#hbg-c)"/><circle cx="40" cy="40" r="38" fill="url(#hinn-c)"/><circle cx="40" cy="40" r="36.5" stroke="#0e7490" stroke-width="1" opacity="0.4" filter="url(#hgw-c)"/><circle cx="40" cy="40" r="37.5" stroke="#22d3ee" stroke-width="1.5" opacity="0.85" filter="url(#hgw-c)"/><circle cx="40" cy="40" r="33" stroke="#0891b2" stroke-width="0.6" stroke-dasharray="3 4" opacity="0.5"/><rect x="16" y="12" width="28" height="38" rx="2.5" fill="#041620" stroke="#22d3ee" stroke-width="1.5" opacity="0.85"/><path d="M38 12 L44 18 L38 18 Z" fill="#0e4f63" stroke="#22d3ee" stroke-width="1" stroke-linejoin="round"/><line x1="21" y1="24" x2="38" y2="24" stroke="#22d3ee" stroke-width="1.2" stroke-linecap="round" opacity="0.6"/><line x1="21" y1="29" x2="38" y2="29" stroke="#22d3ee" stroke-width="1.2" stroke-linecap="round" opacity="0.6"/><line x1="21" y1="34" x2="32" y2="34" stroke="#22d3ee" stroke-width="1.2" stroke-linecap="round" opacity="0.5"/><line x1="21" y1="39" x2="36" y2="39" stroke="#22d3ee" stroke-width="1.2" stroke-linecap="round" opacity="0.4"/><circle cx="48" cy="48" r="12" fill="#041e2a" stroke="#06b6d4" stroke-width="2.2" filter="url(#hgw-c)"/><circle cx="48" cy="48" r="12" stroke="#22d3ee" stroke-width="0.8" opacity="0.4"/><line x1="57" y1="57" x2="65" y2="65" stroke="#06b6d4" stroke-width="3.5" stroke-linecap="round" filter="url(#hgw-c)"/><path d="M42 48 L46 52 L55 43" stroke="#22d3ee" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" filter="url(#hgw-c)"/></svg>`,
    kpm_support: `<svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg"><defs><radialGradient id="hbg-k" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#3b0a0a"/><stop offset="70%" stop-color="#1c0404"/><stop offset="100%" stop-color="#080101"/></radialGradient><radialGradient id="hinn-k" cx="50%" cy="40%" r="50%"><stop offset="0%" stop-color="#dc2626" stop-opacity="0.3"/><stop offset="100%" stop-color="transparent"/></radialGradient><filter id="hgw-k"><feGaussianBlur stdDeviation="2.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs><circle cx="40" cy="40" r="38" fill="url(#hbg-k)"/><circle cx="40" cy="40" r="38" fill="url(#hinn-k)"/><circle cx="40" cy="40" r="36.5" stroke="#991b1b" stroke-width="1" opacity="0.4" filter="url(#hgw-k)"/><circle cx="40" cy="40" r="37.5" stroke="#f87171" stroke-width="1.5" opacity="0.85" filter="url(#hgw-k)"/><circle cx="40" cy="40" r="33" stroke="#dc2626" stroke-width="0.6" stroke-dasharray="3 4" opacity="0.5"/><path d="M40 12 L58 20 V36 C58 50 40 60 40 60 C40 60 22 50 22 36 V20 Z" fill="#1c0404" stroke="#f87171" stroke-width="2" stroke-linejoin="round" filter="url(#hgw-k)"/><path d="M40 16 L54 23 V36 C54 47 40 56 40 56 C40 56 26 47 26 36 V23 Z" fill="none" stroke="#fca5a5" stroke-width="0.8" stroke-linejoin="round" opacity="0.4"/><path d="M30 30 C30 30 34 28 40 30 C46 28 50 30 50 30 V44 C50 44 46 42 40 44 C34 42 30 44 30 44 Z" fill="#3b0a0a" stroke="#fca5a5" stroke-width="1.4" stroke-linejoin="round"/><line x1="40" y1="30" x2="40" y2="44" stroke="#fca5a5" stroke-width="1.2" opacity="0.8"/><line x1="32" y1="34" x2="38" y2="34" stroke="#fca5a5" stroke-width="0.8" opacity="0.6"/><line x1="32" y1="37" x2="38" y2="37" stroke="#fca5a5" stroke-width="0.8" opacity="0.5"/><line x1="32" y1="40" x2="38" y2="40" stroke="#fca5a5" stroke-width="0.8" opacity="0.4"/><line x1="42" y1="34" x2="48" y2="34" stroke="#fca5a5" stroke-width="0.8" opacity="0.6"/><line x1="42" y1="37" x2="48" y2="37" stroke="#fca5a5" stroke-width="0.8" opacity="0.5"/><line x1="42" y1="40" x2="48" y2="40" stroke="#fca5a5" stroke-width="0.8" opacity="0.4"/><rect x="32" y="48" width="16" height="8" rx="2" fill="#7f1d1d" stroke="#f87171" stroke-width="1" filter="url(#hgw-k)"/><text x="40" y="55" text-anchor="middle" font-size="6" font-family="Arial" font-weight="bold" fill="#fca5a5">KPM</text></svg>`,
};

const AGENT_INFO = {
    data_analysis: {
        icon: AGENT_ICONS.data_analysis,
        name: { bm: 'Analisis Data', en: 'Data Analysis' },
        desc: { bm: 'Muat naik fail CSV/Excel dan tanya soalan tentang data anda. Saya akan menjana carta, statistik dan analisis.', en: 'Upload CSV/Excel files and ask questions about your data. I will generate charts, statistics and analysis.' },
        quick: { bm: ['Tunjukkan ringkasan statistik', 'Buat carta berdasarkan data', 'Ada data yang kosong?', 'Senaraikan semua lajur'], en: ['Show statistical summary', 'Create chart from data', 'Any missing data?', 'List all columns'] },
    },
    letter_generator: {
        icon: AGENT_ICONS.letter_generator,
        name: { bm: 'Penjana Surat Rasmi', en: 'Official Letter Generator' },
        desc: { bm: 'Bantu anda menyediakan surat rasmi, memo dan surat siaran mengikut format KPM.', en: 'Help you draft official letters, memos and circulars in KPM format.' },
        quick: { bm: ['Tulis surat jemputan bengkel', 'Buat memo dalaman', 'Tulis surat siaran'], en: ['Write workshop invitation letter', 'Create internal memo', 'Write circular letter'] },
    },
    report_generator: {
        icon: AGENT_ICONS.report_generator,
        name: { bm: 'Penjana Laporan', en: 'Report Generator' },
        desc: { bm: 'Jana laporan satu muka surat (One Page Report) dalam format rasmi PPD/KPM.', en: 'Generate one-page reports in official PPD/KPM format.' },
        quick: { bm: ['Jana laporan bengkel ICT', 'Buat laporan program motivasi', 'Sediakan laporan lawatan'], en: ['Generate ICT workshop report', 'Create motivation program report', 'Prepare visit report'] },
    },
    document_reviewer: {
        icon: AGENT_ICONS.document_reviewer,
        name: { bm: 'Semakan Dokumen', en: 'Document Review' },
        desc: { bm: 'Semak tatabahasa, ejaan, format dan pematuhan dokumen rasmi KPM anda.', en: 'Check grammar, spelling, format and compliance of your KPM documents.' },
        quick: { bm: ['Semak surat rasmi saya', 'Periksa format laporan ini', 'Review memo dalaman'], en: ['Review my official letter', 'Check this report format', 'Review internal memo'] },
    },
    kpm_support: {
        icon: AGENT_ICONS.kpm_support,
        name: { bm: 'Sokongan KPM', en: 'KPM Support' },
        desc: { bm: 'Bantuan untuk sistem EMIS, APDM, DTPCare dan soalan polisi/prosedur KPM.', en: 'Help with EMIS, APDM, DTPCare systems and KPM policies/procedures.' },
        quick: { bm: ['Cara semak ralat EMIS', 'Masalah login APDM', 'Cara isi modul infrastruktur', 'Panduan pengurusan DTP'], en: ['How to check EMIS errors', 'APDM login issues', 'How to fill infrastructure module', 'DTP management guide'] },
    },
};

function getAgentInfo(agentKey) {
    const raw = AGENT_INFO[agentKey];
    if (!raw) return { icon: '', name: agentKey, desc: '', quick: [] };
    return {
        icon: raw.icon,
        name: raw.name[currentLang] || raw.name.bm,
        desc: raw.desc[currentLang] || raw.desc.bm,
        quick: raw.quick[currentLang] || raw.quick.bm,
    };
}

// ═══ Particle Background ═══
function initParticles() {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let w, h, particles = [];

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    const colors = ['#4f46e5', '#7c3aed', '#0891b2', '#d97706', '#059669', '#dc2626', '#2563eb'];
    for (let i = 0; i < 80; i++) {
        particles.push({
            x: Math.random() * w, y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.4, vy: (Math.random() - 0.5) * 0.4,
            r: Math.random() * 2.5 + 1,
            color: colors[Math.floor(Math.random() * colors.length)],
        });
    }

    function draw() {
        ctx.clearRect(0, 0, w, h);
        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0) p.x = w; if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h; if (p.y > h) p.y = 0;
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = p.color; ctx.fill();

            for (let j = i + 1; j < particles.length; j++) {
                const q = particles[j];
                const dx = p.x - q.x, dy = p.y - q.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 150) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y);
                    ctx.strokeStyle = `rgba(79,70,229,${0.12 * (1 - dist / 150)})`;
                    ctx.lineWidth = 0.5; ctx.stroke();
                }
            }
        }
        requestAnimationFrame(draw);
    }
    draw();
}
initParticles();

// ═══ Navigation ═══

function openAgent(agentKey, existingSessionId) {
    currentAgent = agentKey;
    _activeLetterMsgDiv = null;
    lastActiveAgent = agentKey;
    sessionId = existingSessionId || 'sess_' + agentKey + '_' + Date.now();

    const info = getAgentInfo(agentKey);

    document.getElementById('canvasAgentIcon').innerHTML = info.icon;
    document.getElementById('canvasAgentName').textContent = info.name;
    document.getElementById('canvasWelcomeIcon').innerHTML = info.icon;
    document.getElementById('canvasWelcomeTitle').textContent = info.name;
    document.getElementById('canvasWelcomeDesc').textContent = info.desc;

    const quickDiv = document.getElementById('canvasQuickActions');
    quickDiv.innerHTML = info.quick.map(q =>
        `<button class="canvas-quick-btn" onclick="useQuickAction('${escapeAttr(q)}')">${escapeHtml(q)}</button>`
    ).join('');

    const showUpload = agentKey === 'data_analysis' || agentKey === 'document_reviewer';
    uploadBtn.style.display = showUpload ? '' : 'none';
    if (agentKey === 'document_reviewer') {
        fileInput.accept = '.pdf,.docx,.doc';
        uploadBtn.title = 'Muat naik PDF atau Word untuk semakan';
    } else {
        fileInput.accept = '.csv,.xlsx,.xls';
        uploadBtn.title = 'Muat naik fail CSV/Excel';
    }
    hasUploadedData = false;
    fileIndicator.style.display = 'none';

    // Clear messages, show welcome
    const msgs = canvasMessages.querySelectorAll('.message');
    msgs.forEach(m => m.remove());
    canvasWelcome.style.display = '';

    landingPage.style.display = 'none';
    agentCanvas.style.display = 'flex';
    chatInput.focus();
    updateAgentNavBar(agentKey);
    const sidebarTools = document.getElementById('sidebarTools');
    if (sidebarTools) {
        sidebarTools.style.display = (agentKey === 'letter_generator' || agentKey === 'report_generator') ? 'flex' : 'none';
    }

    if (existingSessionId) {
        loadSessionMessages(existingSessionId);
    } else {
        loadCanvasHistory(agentKey);
        sendAgentIntro(agentKey);
    }
}

function updateAgentNavBar(activeKey) {
    const navBar = document.getElementById('agentNavBar');
    if (!navBar) return;
    const agentKeys = ['data_analysis', 'report_generator', 'letter_generator', 'document_reviewer', 'kpm_support'];
    navBar.innerHTML = agentKeys.map(key => {
        const info = getAgentInfo(key);
        const isActive = key === activeKey;
        return `<button class="agent-nav-btn${isActive ? ' active' : ''}" onclick="switchAgent('${key}')" title="${info.name}">
            <span class="agent-nav-icon">${info.icon}</span>
            <span class="agent-nav-label">${info.name}</span>
        </button>`;
    }).join('');
}

function switchAgent(agentKey) {
    if (agentKey === currentAgent) return;
    openAgent(agentKey);
}

async function sendAgentIntro(agentKey) {
    const info = getAgentInfo(agentKey);
    typingIndicator.classList.add('active');
    try {
        const res = await fetch('/api/agent-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: '__INTRO__', agent: agentKey, session_id: sessionId, lang: currentLang }),
        });
        const data = await res.json();
        typingIndicator.classList.remove('active');
        addMessage(data.response, 'assistant', info.icon, info.name);
    } catch (_) {
        typingIndicator.classList.remove('active');
    }
}

async function sendFarewell() {
    if (!currentAgent || !sessionId) return;
    const msgs = canvasMessages.querySelectorAll('.message');
    if (msgs.length === 0) return;
    const info = getAgentInfo(currentAgent);
    const farewellMsg = currentLang === 'en'
        ? `Thank you for using SMARTAssist Hub ${info.name}. Have a great day! 😊`
        : `Terima kasih kerana menggunakan khidmat SMARTAssist Hub ${info.name}. Semoga hari tuan/puan menyenangkan! 😊`;
    addMessage(farewellMsg, 'assistant', info.icon, info.name);
    await new Promise(r => setTimeout(r, 2500));
}

async function loadCanvasHistory(agentKey) {
    const existing = document.getElementById('canvasHistorySection');
    if (existing) existing.remove();
    try {
        const res = await fetch('/api/sessions');
        const sessions = await res.json();
        const filtered = sessions.filter(s => s.agent === agentKey).slice(0, 5);
        if (filtered.length === 0) return;

        const label = currentLang === 'bm' ? 'Sesi Lepas' : 'Recent Sessions';
        const section = document.createElement('div');
        section.id = 'canvasHistorySection';
        section.className = 'canvas-history-section';
        section.innerHTML = `<div class="canvas-history-label">${label}</div>
            <div class="canvas-history-items">${filtered.map(s => {
                const info = getAgentInfo(s.agent);
                const time = new Date(s.updated).toLocaleString('ms-MY', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
                return `<div class="canvas-history-item" onclick="loadSession('${escapeAttr(s.session_id)}', '${escapeAttr(s.agent)}')">
                    <div class="canvas-history-item-icon">${info.icon}</div>
                    <div class="canvas-history-item-info">
                        <div class="canvas-history-item-title">${escapeHtml(s.title)}</div>
                        <div class="canvas-history-item-meta">${time} &middot; ${s.message_count} mesej</div>
                    </div>
                </div>`;
            }).join('')}</div>`;
        canvasWelcome.appendChild(section);
    } catch (_) {}
}

async function goHome() {
    await sendFarewell();
    agentCanvas.style.display = 'none';
    landingPage.style.display = '';
    currentAgent = null;
    sessionId = null;
    refreshHistory();
}

async function newSession() {
    if (!currentAgent) return;
    await sendFarewell();
    openAgent(currentAgent);
}

async function loadSessionMessages(sid) {
    try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(sid)}/messages`);
        const messages = await res.json();
        if (messages.length > 0) {
            canvasWelcome.style.display = 'none';
            messages.forEach(msg => {
                if (msg.role === 'user') {
                    addMessage(msg.content, 'user');
                } else {
                    let structured = null;
                    try { structured = JSON.parse(msg.content); } catch (_) {}
                    addMessage(msg.content, 'assistant', msg.agent_icon, msg.agent_name, structured);
                }
            });
        }
    } catch (_) {}
}

// ═══ History Panel ═══

function toggleHistory() {
    historyPanel.classList.toggle('open');
    historyOverlay.classList.toggle('open');
    if (historyPanel.classList.contains('open')) refreshHistory();
}

async function refreshHistory() {
    try {
        const res = await fetch('/api/sessions');
        const sessions = await res.json();
        if (sessions.length === 0) {
            historyList.innerHTML = '<div class="history-empty">Tiada sejarah sesi lagi.</div>';
            return;
        }
        historyList.innerHTML = sessions.map(s => {
            const info = s.agent ? getAgentInfo(s.agent) : { icon: '\u{1F4AC}', name: s.agent };
            const time = new Date(s.updated).toLocaleString('ms-MY', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
            return `<div class="history-item" onclick="loadSession('${escapeAttr(s.session_id)}', '${escapeAttr(s.agent)}')">
                <div class="history-item-icon">${info.icon}</div>
                <div class="history-item-info">
                    <div class="history-item-title">${escapeHtml(s.title)}</div>
                    <div class="history-item-meta">${info.name} &middot; ${time} &middot; ${s.message_count} mesej</div>
                </div>
                <button class="history-item-delete" onclick="event.stopPropagation(); deleteSession('${escapeAttr(s.session_id)}')" title="Padam">&times;</button>
            </div>`;
        }).join('');
    } catch (_) {
        historyList.innerHTML = '<div class="history-empty">Gagal memuatkan sejarah.</div>';
    }
}

function loadSession(sid, agent) {
    toggleHistory();
    openAgent(agent, sid);
}

async function deleteSession(sid) {
    try {
        await fetch('/api/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sid, message: '' }),
        });
        refreshHistory();
    } catch (_) {}
}

// ═══ Messages ═══

function addMessage(content, role, agentIcon, agentName, structured) {
    if (canvasWelcome) canvasWelcome.style.display = 'none';

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    let html = '';
    if (role === 'assistant' && agentName) {
        html += `<div class="agent-tag">${agentIcon} ${agentName}</div>`;
    }

    if (structured && structured.response_type) {
        lastStructuredData = structured;
        html += buildStructuredHtml(structured);
    } else if (structured && structured.issues !== undefined) {
        html += buildReviewHtml(structured);
    } else if (structured && structured.phase !== undefined) {
        html += buildLetterHtml(structured);
    } else {
        html += `<div class="message-bubble">${escapeHtml(content)}</div>`;
    }

    if (role === 'assistant') {
        const idx = _msgIndex++;
        html += `<div class="msg-feedback">
            <button class="feedback-btn" id="fb-up-${idx}" onclick="submitFeedback(${idx}, 'up')" title="Berguna">👍</button>
            <button class="feedback-btn" id="fb-down-${idx}" onclick="submitFeedback(${idx}, 'down')" title="Tidak berguna">👎</button>
        </div>`;
    }

    msgDiv.innerHTML = html;

    // === In-place fix intercept — update pratonton dalam mesej asal, tambah butang Undo ===
    if (structured && structured.corrected_document && _pendingFixBtn) {
        const previewSection = _pendingFixMsgDiv?.querySelector('.review-doc-preview-section');
        const previewEl = _pendingFixMsgDiv?.querySelector('#reviewDocPreview');
        if (previewSection && previewEl) {
            _undoReviewState = { msgDiv: _pendingFixMsgDiv, content: previewEl.textContent };
            previewEl.textContent = structured.corrected_document;
            previewSection.style.display = '';
            saveDocumentEdits(structured.corrected_document);
            const docActions = previewSection.querySelector('.doc-actions');
            if (docActions && !docActions.querySelector('.undo-fix-btn')) {
                const undoBtn = document.createElement('button');
                undoBtn.className = 'doc-action-btn undo-fix-btn';
                undoBtn.textContent = '↩️ Batal Pembetulan';
                undoBtn.onclick = undoReviewFix;
                docActions.appendChild(undoBtn);
            }
            setTimeout(() => previewSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
        }
        _pendingFixBtn.textContent = '✅ Berjaya Dibetulkan';
        _pendingFixBtn.classList.remove('fix-processing');
        _pendingFixBtn.classList.add('fix-done');
        _pendingFixBtn.disabled = true;
        _pendingFixBtn = null;
        _pendingFixMsgDiv = null;
        return;
    }
    if (structured && structured.document_preview && _pendingLetterFixBtn) {
        const existingPreview = _pendingLetterMsgDiv?.querySelector('#docPreview');
        const existingPreviewHtml = _pendingLetterMsgDiv?.querySelector('#docPreviewHtml');
        const previewSection = _pendingLetterMsgDiv?.querySelector('.doc-preview-section');
        _undoLetterState = {
            msgDiv: _pendingLetterMsgDiv,
            content: existingPreview?.textContent || '',
            htmlContent: existingPreviewHtml?.innerHTML || ''
        };
        if (existingPreview) existingPreview.textContent = structured.document_preview;
        if (existingPreviewHtml && structured.document_html) existingPreviewHtml.innerHTML = structured.document_html;
        if (previewSection && !previewSection.querySelector('.undo-fix-btn')) {
            const undoBtn = document.createElement('button');
            undoBtn.className = 'doc-action-btn undo-fix-btn';
            undoBtn.textContent = '↩️ Batal Pembetulan';
            undoBtn.onclick = undoLetterFix;
            previewSection.appendChild(undoBtn);
        }
        if (structured.auto_review) {
            const reviewPanel = _pendingLetterMsgDiv?.querySelector('.auto-review-panel');
            if (reviewPanel) {
                const tmp = document.createElement('div');
                tmp.innerHTML = renderAutoReviewPanel(structured.auto_review);
                reviewPanel.replaceWith(tmp.firstElementChild);
            }
        }
        _pendingLetterFixBtn.textContent = '✅ Berjaya Dibetulkan';
        _pendingLetterFixBtn.classList.remove('fix-processing');
        _pendingLetterFixBtn.classList.add('fix-done');
        _pendingLetterFixBtn.disabled = true;
        _pendingLetterFixBtn = null;
        _pendingLetterMsgDiv = null;
        setTimeout(() => (existingPreviewHtml || existingPreview)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
        return;
    }
    // === Tamat in-place intercept ===

    // In-place update for all letter/report agent responses after the first
    if (structured && structured.phase !== undefined && _activeLetterMsgDiv) {
        _activeLetterMsgDiv.innerHTML = msgDiv.innerHTML;
        // Re-attach chart if any
        if (structured.chart) renderChart(_activeLetterMsgDiv, structured.chart);
        setTimeout(() => _activeLetterMsgDiv.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
        return;
    }

    canvasMessages.insertBefore(msgDiv, typingIndicator);
    canvasMessages.scrollTop = canvasMessages.scrollHeight;
    // Track active letter/report message div for in-place updates
    if (structured && structured.phase !== undefined) {
        _activeLetterMsgDiv = msgDiv;
    }
    if (document.getElementById('reportImgGrid')) {
        _refreshReportImages();
    }
    if (structured && structured.chart) {
        renderChart(msgDiv, structured.chart);
    }
}

async function submitFeedback(idx, type) {
    const upBtn = document.getElementById(`fb-up-${idx}`);
    const downBtn = document.getElementById(`fb-down-${idx}`);
    if (!upBtn || !downBtn) return;
    upBtn.classList.remove('active-up'); downBtn.classList.remove('active-down');
    if (type === 'up') upBtn.classList.add('active-up');
    else downBtn.classList.add('active-down');
    try {
        await fetch('/api/feedback', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId || 'default', message_index: idx, feedback: type, agent: currentAgent || '' }),
        });
    } catch (_) {}
}

function buildStructuredHtml(data) {
    let html = '<div class="message-bubble structured-response">';

    html += `<div class="da-message">${escapeHtml(data.message || '')}</div>`;

    if (data.penemuan && data.penemuan.length) {
        html += '<div class="da-section"><div class="da-section-title">\u{1F50D} Penemuan</div><ul>';
        data.penemuan.forEach(p => { html += `<li>${escapeHtml(p)}</li>`; });
        html += '</ul></div>';
    }

    if (data.tafsiran) {
        html += `<div class="da-section"><div class="da-section-title">\u{1F4A1} Tafsiran</div><p style="font-size:13px;color:var(--text-secondary);line-height:1.6">${escapeHtml(data.tafsiran)}</p></div>`;
    }

    if (data.cadangan && data.cadangan.length) {
        html += '<div class="da-section"><div class="da-section-title">\u{2705} Cadangan</div><ul>';
        data.cadangan.forEach(c => { html += `<li>${escapeHtml(c)}</li>`; });
        html += '</ul></div>';
    }

    if (data.amaran && data.amaran.length) {
        html += '<div class="da-section da-warning"><div class="da-section-title">\u{26A0}\u{FE0F} Amaran</div><ul>';
        data.amaran.forEach(a => { html += `<li>${escapeHtml(a)}</li>`; });
        html += '</ul></div>';
    }

    if (data.susulan && data.susulan.length) {
        html += '<div class="da-section"><div class="da-section-title">\u{1F4AC} Soalan Susulan</div>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px;">';
        data.susulan.forEach(s => {
            html += `<button class="canvas-quick-btn" onclick="useQuickAction('${escapeAttr(s)}')">${escapeHtml(s)}</button>`;
        });
        html += '</div></div>';
    }

    if (data.table) {
        html += buildTableHtml(data.table);
    }

    if (data.chart) {
        const chartId = 'chart_' + (++chartCounter);
        html += `<div class="da-section da-chart-wrapper" id="wrap_${chartId}">`;
        html += `<div class="da-chart-toolbar"><button class="chart-tool-btn" onclick="toggleChartSize(this)" title="Kembang/Kecilkan">\u{1F50D}</button></div>`;
        html += `<div class="da-chart-container"><canvas id="${chartId}"></canvas></div></div>`;
    }

    // Export buttons
    html += '<div class="da-export-actions">';
    html += `<button class="da-export-btn pptx-btn" onclick="downloadAnalysis('pptx')">\u{1F4CA} PowerPoint</button>`;
    html += `<button class="da-export-btn pdf-btn" onclick="downloadAnalysis('pdf')">\u{1F4C4} PDF</button>`;
    html += `<button class="da-export-btn csv-btn" onclick="downloadAnalysis('csv')">\u{1F4E5} CSV</button>`;
    html += '</div>';

    html += '</div>';
    return html;
}

function buildTableHtml(table) {
    if (!table || !table.headers || !table.rows) return '';
    const tblId = 'tbl_' + (++chartCounter);
    let html = '<div class="da-section da-table-section">';
    html += '<div class="da-table-toolbar">';
    html += `<input class="da-table-filter" placeholder="Cari..." oninput="filterTable('${tblId}', this.value)">`;
    html += `<button class="da-export-btn csv-btn" onclick="downloadTableCSV('${tblId}')" style="flex-shrink:0">\u{1F4E5} CSV</button>`;
    html += '</div>';
    html += `<table class="da-table" id="${tblId}"><thead><tr>`;
    table.headers.forEach((h, i) => {
        html += `<th class="sortable-th" onclick="sortTable('${tblId}', ${i})">${escapeHtml(h)} <span class="sort-icon">\u{21C5}</span></th>`;
    });
    html += '</tr></thead><tbody>';
    table.rows.forEach(row => {
        html += '<tr>' + row.map(c => `<td>${escapeHtml(String(c))}</td>`).join('') + '</tr>';
    });
    html += '</tbody></table></div>';
    return html;
}

function buildReviewHtml(data) {
    let html = '<div class="message-bubble structured-response review-response">';

    if (data.message) {
        html += `<div class="da-message">${escapeHtml(data.message)}</div>`;
    }

    if (data.summary) {
        html += `<div class="da-section"><div class="da-section-title">\u{1F4CB} Ringkasan Semakan</div>`;
        html += `<p style="font-size:13px;color:var(--text-secondary);line-height:1.6">${escapeHtml(data.summary)}</p>`;
        if (data.score) {
            const scoreColors = { A: '#22c55e', B: '#3b82f6', C: '#f59e0b', D: '#ef4444' };
            const scoreLabels = { A: 'Cemerlang', B: 'Baik', C: 'Perlu Pembetulan', D: 'Banyak Isu' };
            const color = scoreColors[data.score] || '#888';
            const label = scoreLabels[data.score] || data.score;
            html += `<div class="review-score" style="color:${color};font-weight:bold;font-size:1.1em;margin-top:6px;">Skor: ${data.score} — ${label}</div>`;
        }
        html += '</div>';
    }

    if (data.issues && data.issues.length > 0) {
        const mustFix = data.issues.filter(i => i.severity === 'WAJIB_BETULKAN');
        const suggestions = data.issues.filter(i => i.severity !== 'WAJIB_BETULKAN');
        const _reviewMsgId = 'rev_' + Date.now();

        if (mustFix.length > 0) {
            html += '<div class="da-section"><div class="da-section-title">\u{1F6A8} Wajib Betulkan (' + mustFix.length + ')</div>';
            html += '<div class="review-issues">';
            mustFix.forEach((issue, idx) => {
                const btnId = `${_reviewMsgId}_mf${idx}`;
                const fixPrompt = issue.suggestion
                    ? `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.suggestion}`
                    : `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.issue || ''}`;
                html += `<div class="review-issue must-fix">`;
                html += `<div class="issue-header"><span class="issue-num">${idx + 1}</span><span class="issue-cat">${escapeHtml(issue.category || '')}</span></div>`;
                html += `<div class="issue-location">${escapeHtml(issue.location || '')}</div>`;
                html += `<div class="issue-desc">${escapeHtml(issue.issue || '')}</div>`;
                if (issue.suggestion) html += `<div class="issue-suggestion">\u{1F4A1} ${escapeHtml(issue.suggestion)}</div>`;
                html += `<button class="issue-fix-btn" id="${btnId}" data-prompt="${escapeAttr(fixPrompt)}" onclick="fixReviewIssue(this)">🔧 Betulkan</button>`;
                html += '</div>';
            });
            html += '</div></div>';
        }

        if (suggestions.length > 0) {
            html += '<div class="da-section"><div class="da-section-title">\u{1F4A1} Cadangan (' + suggestions.length + ')</div>';
            html += '<div class="review-issues">';
            suggestions.forEach((issue, idx) => {
                const btnId = `${_reviewMsgId}_cd${idx}`;
                const fixPrompt = issue.suggestion
                    ? `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.suggestion}`
                    : `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.issue || ''}`;
                html += `<div class="review-issue suggestion">`;
                html += `<div class="issue-header"><span class="issue-num">${idx + 1}</span><span class="issue-cat">${escapeHtml(issue.category || '')}</span></div>`;
                html += `<div class="issue-location">${escapeHtml(issue.location || '')}</div>`;
                html += `<div class="issue-desc">${escapeHtml(issue.issue || '')}</div>`;
                if (issue.suggestion) html += `<div class="issue-suggestion">\u{1F4A1} ${escapeHtml(issue.suggestion)}</div>`;
                html += `<button class="issue-fix-btn issue-fix-btn--cadangan" id="${btnId}" data-prompt="${escapeAttr(fixPrompt)}" onclick="fixReviewIssue(this)">🔧 Betulkan</button>`;
                html += '</div>';
            });
            html += '</div></div>';
        }
    } else if (data.issues && data.issues.length === 0) {
        html += '<div class="da-section"><div class="da-section-title">\u{2705} Tiada Isu Ditemui</div>';
        html += '<p style="font-size:13px;color:var(--text-secondary)">Dokumen ini dalam keadaan baik.</p></div>';
    }

    html += `<div class="da-section doc-preview-section review-doc-preview-section" style="${data.corrected_document ? '' : 'display:none'}">`;
    html += `<div class="da-section-title">\u{1F4C4} Dokumen Diperbetulkan <span class="edit-hint">(boleh diedit)</span></div>`;
    html += `<pre class="doc-preview" contenteditable="true" id="reviewDocPreview">${data.corrected_document ? escapeHtml(data.corrected_document) : ''}</pre>`;
    const remindMsgRev = currentLang === 'en'
        ? '⚠️ Please review the corrected document carefully before downloading. Ensure all information is accurate and complete.'
        : '⚠️ Sila semak semula dokumen yang telah diperbetulkan sebelum dimuat turun. Pastikan semua maklumat adalah tepat dan lengkap.';
    html += `<div class="doc-review-reminder">${remindMsgRev}</div>`;
    html += `<div class="doc-actions"><button class="doc-action-btn download-btn" onclick="downloadReviewDocument()">\u{1F4E5} Muat Turun (.docx)</button></div>`;
    html += '</div>';

    html += '</div>';
    return html;
}

// ═══ Inline fields form (replaces "BELUM DIISI" list) ═══

const _FIELD_DEFS = {
    'Nombor Rujukan':                         { type: 'text',     ph: 'cth: KPM.600-1/1/3 (JPN)' },
    'Nombor Rujukan (Ruj. Kami)':             { type: 'text',     ph: 'cth: KPM.600-1/1/3 (JPN)' },
    'Tarikh':                                 { type: 'date',     ph: '' },
    'Tarikh Memo':                            { type: 'date',     ph: '' },
    'Tarikh Acara':                           { type: 'date',     ph: '' },
    'Tarikh Program':                         { type: 'date',     ph: '' },
    'Tarikh Disediakan':                      { type: 'date',     ph: '' },
    'Nama Penerima':                          { type: 'text',     ph: 'cth: Encik Ahmad bin Ali' },
    'Jawatan Penerima':                       { type: 'text',     ph: 'cth: Pengetua' },
    'Nama Organisasi Penerima':               { type: 'text',     ph: 'cth: SMK Taman Maju' },
    'Alamat Penerima':                        { type: 'textarea', ph: 'Alamat penuh penerima...' },
    'Perkara / Tajuk Surat':                  { type: 'text',     ph: 'Tajuk surat...' },
    'Perkara / Tajuk Memo (huruf besar)':     { type: 'text',     ph: 'TAJUK MEMO (HURUF BESAR)' },
    'Nama Pengerusi dan Jawatan':             { type: 'text',     ph: 'cth: Pn. Zainab bt. Ahmad, Pengetua' },
    'Nama Penyelaras dan Jawatan':            { type: 'text',     ph: 'cth: En. Farid bin Ismail, GPK HEM' },
    'Nama Ahli-Ahli (pisahkan dengan koma)':  { type: 'ahli-list', ph: '' },
    'Nama Urus Setia dan Jawatan':            { type: 'text',     ph: 'cth: En. Farid bin Ismail, Guru' },
    'Masa Acara':                             { type: 'text',     ph: 'cth: 8.00 pagi' },
    'Tempat Acara':                           { type: 'text',     ph: 'cth: Bilik Mesyuarat Utama' },
    'Nama Penandatangan':                     { type: 'text',     ph: 'cth: Encik Ahmad bin Ali' },
    'Jawatan Penandatangan':                  { type: 'text',     ph: 'cth: Pengetua' },
    'Nama Pejabat':                           { type: 'text',     ph: 'cth: Jabatan Pendidikan Negeri' },
    'Salinan Kepada (s.k.)':                  { type: 'text',     ph: 'Nama dan jawatan (pilihan)' },
    'Nama Program':                           { type: 'text',     ph: 'cth: Program Latihan Guru 2026' },
    'Hari':                                   { type: 'text',     ph: 'auto-isi apabila tarikh dipilih' },
    'Masa Program':                           { type: 'text',     ph: 'cth: 8.00 pagi' },
    'Nama Organisasi':                        { type: 'text',     ph: 'cth: Pejabat Pendidikan Daerah Dalat' },
    'Nama Pegawai Yang Terlibat':             { type: 'textarea', ph: 'cth: Ahmad bin Ali, Pen PPD\nSiti binti Rahman, Pen PPD' },
    'Jawatan Pegawai Yang Terlibat':          { type: 'text',     ph: 'cth: Penolong PPD' },
    'Objektif Program':                       { type: 'textarea', ph: 'Nyatakan objektif program...' },
    'Nama Penyedia Laporan':                  { type: 'text',     ph: 'cth: Ahmad bin Ali' },
    'Jawatan Penyedia':                       { type: 'text',     ph: 'cth: Penolong PPD' },
    'Nama Pengesah Laporan':                  { type: 'text',     ph: 'cth: Encik Zulkifli bin Hamid' },
    'Jawatan Pengesah':                       { type: 'text',     ph: 'cth: Pegawai Pendidikan Daerah' },
};

const _MS_DAYS   = ['Ahad','Isnin','Selasa','Rabu','Khamis','Jumaat','Sabtu'];
const _MS_MONTHS = ['Januari','Februari','Mac','April','Mei','Jun','Julai','Ogos','September','Oktober','November','Disember'];

function _formatDateMS(iso) {
    if (!iso) return '';
    const [y, m, d] = iso.split('-').map(Number);
    const dt = new Date(y, m - 1, d);
    return `${d} ${_MS_MONTHS[m - 1]} ${y} (${_MS_DAYS[dt.getDay()]})`;
}

let _formCounter = 0;

function _buildMissingFieldsForm(missingLabels) {
    if (!missingLabels || missingLabels.length === 0) return '';
    const fid = 'ff_' + (++_formCounter);
    let html = `<div class="da-section fields-form-section">
        <div class="da-section-title">\u{1F4DD} Sila Isikan Maklumat</div>
        <form class="fields-form" id="${fid}" onsubmit="event.preventDefault();_submitFieldsForm('${fid}')">`;
    missingLabels.forEach(label => {
        const def = _FIELD_DEFS[label] || { type: 'text', ph: '' };
        const iid = `${fid}_${label.replace(/\W/g,'_')}`;
        html += `<div class="ff-field">
            <label class="ff-label" for="${iid}">${escapeHtml(label)}</label>`;
        if (def.type === 'ahli-list') {
            html += `<div class="ff-ahli-list" id="${iid}" data-label="${escapeAttr(label)}">
                <div class="ff-ahli-row">
                    <input class="ff-input ff-ahli-nama" type="text" placeholder="Nama ahli">
                    <input class="ff-input ff-ahli-jawatan" type="text" placeholder="Jawatan">
                    <button type="button" class="ff-ahli-remove" onclick="_removeAhliRow(this)" title="Buang">✕</button>
                </div>
            </div>
            <button type="button" class="ff-ahli-add" onclick="_addAhliRow('${iid}')">＋ Tambah Ahli</button>`;
        } else if (def.type === 'textarea') {
            html += `<textarea class="ff-input" id="${iid}" data-label="${escapeAttr(label)}" placeholder="${escapeAttr(def.ph)}" rows="2"></textarea>`;
        } else if (def.type === 'date') {
            html += `<input class="ff-input ff-date" type="date" id="${iid}" data-label="${escapeAttr(label)}" data-is-date="1" onchange="_onDateChange(this,'${fid}')">`;
        } else {
            html += `<input class="ff-input" type="text" id="${iid}" data-label="${escapeAttr(label)}" placeholder="${escapeAttr(def.ph)}">`;
        }
        html += `</div>`;
    });
    html += `<button type="submit" class="ff-submit-btn">\u{1F4E4} Hantar Maklumat</button>
        </form></div>`;
    return html;
}

function _onDateChange(input, fid) {
    if (!input.value) return;
    const [y, m, d] = input.value.split('-').map(Number);
    const day = _MS_DAYS[new Date(y, m - 1, d).getDay()];
    const form = document.getElementById(fid);
    if (!form) return;
    const hariEl = Array.from(form.querySelectorAll('[data-label]')).find(e => e.dataset.label === 'Hari');
    if (hariEl && !hariEl.value) hariEl.value = day;
}

function _addAhliRow(listId) {
    const list = document.getElementById(listId);
    if (!list) return;
    const row = document.createElement('div');
    row.className = 'ff-ahli-row';
    row.innerHTML = `<input class="ff-input ff-ahli-nama" type="text" placeholder="Nama ahli">
        <input class="ff-input ff-ahli-jawatan" type="text" placeholder="Jawatan">
        <button type="button" class="ff-ahli-remove" onclick="_removeAhliRow(this)" title="Buang">✕</button>`;
    list.appendChild(row);
}

function _removeAhliRow(btn) {
    const list = btn.closest('.ff-ahli-list');
    if (!list) return;
    if (list.querySelectorAll('.ff-ahli-row').length <= 1) return;
    btn.closest('.ff-ahli-row').remove();
}

function _submitFieldsForm(fid) {
    const form = document.getElementById(fid);
    if (!form) return;
    const parts = [];
    form.querySelectorAll('[data-label]').forEach(el => {
        if (el.classList.contains('ff-ahli-list')) {
            const entries = [];
            el.querySelectorAll('.ff-ahli-row').forEach(row => {
                const nama = row.querySelector('.ff-ahli-nama').value.trim();
                const jawatan = row.querySelector('.ff-ahli-jawatan').value.trim();
                if (nama) entries.push(jawatan ? `${nama} (${jawatan})` : nama);
            });
            if (entries.length) parts.push(`${el.dataset.label}: ${entries.join(', ')}`);
        } else {
            let val = el.value.trim();
            if (!val) return;
            if (el.dataset.isDate) val = _formatDateMS(val);
            parts.push(`${el.dataset.label}: ${val}`);
        }
    });
    if (parts.length === 0) { showToast('Sila isi sekurang-kurangnya satu medan.', false); return; }
    form.querySelectorAll('input,textarea,button').forEach(el => el.disabled = true);
    form.querySelector('.ff-submit-btn').textContent = '⏳ Menghantar...';
    _suppressUserMsg = true;
    const inp = document.getElementById('chatInput');
    inp.value = parts.join('. ');
    inp.dispatchEvent(new Event('input'));
    document.getElementById('sendBtn').click();
}

// ═══════════════════════════════════════════════════

function buildLetterHtml(data) {
    let html = '<div class="message-bubble structured-response">';

    html += `<div class="da-message">${escapeHtml(data.message || '')}</div>`;

    // Maklumat terkumpul disembunyikan — bekerja di belakang tabir

    if (data.fields_status && data.fields_status.missing && data.fields_status.missing.length > 0) {
        html += _buildMissingFieldsForm(data.fields_status.missing);
    }

    if (data.document_preview) {
        html += '<div class="da-section doc-preview-section">';
        html += '<div class="da-section-title">\u{1F4C4} Pratonton Dokumen <span class="edit-hint">(boleh diedit)</span>'
            + `<button class="doc-preview-expand-btn" onclick="openWordPreview()" title="Besar">&#9974; Lihat Word</button></div>`;
        if (data.document_html) {
            html += `<pre class="doc-preview" contenteditable="true" id="docPreview" style="display:none">${escapeHtml(data.document_preview)}</pre>`;
            html += `<div class="doc-preview doc-preview-html" contenteditable="true" id="docPreviewHtml">${data.document_html}</div>`;
        } else {
            html += `<pre class="doc-preview" contenteditable="true" id="docPreview">${escapeHtml(data.document_preview)}</pre>`;
        }
        html += '</div>';
    }

    if (data.validation_errors && data.validation_errors.length > 0) {
        html += '<div class="da-section da-warning"><div class="da-section-title">\u{26A0}\u{FE0F} Ralat</div><ul>';
        data.validation_errors.forEach(e => { html += `<li>${escapeHtml(e)}</li>`; });
        html += '</ul></div>';
    }

    if (data.auto_review) {
        html += renderAutoReviewPanel(data.auto_review);
    }

    // Image upload panel for report generator
    if (data.awaiting_images && currentAgent === 'report_generator') {
        const imgCount = data.image_count || 0;
        const maxImg = data.max_images || 4;
        html += `<div class="da-section report-img-section" id="reportImgSection">
            <div class="da-section-title">📷 Lampiran Gambar (<span id="reportImgCounter">${imgCount}</span>/${maxImg})</div>
            <p class="report-img-hint">📷 <strong>Langkah Akhir:</strong> Laporan anda telah siap! Sila muat naik sehingga ${maxImg} gambar <strong>landscape</strong> untuk dilampirkan dalam laporan. Gunakan butang '+ Tambah Gambar' di bawah, atau terus muat turun jika tiada gambar diperlukan.</p>
            <div class="report-img-grid" id="reportImgGrid"></div>
            <button class="report-img-add-btn" id="reportImgAddBtn" onclick="triggerReportImageUpload()" ${imgCount >= maxImg ? 'style="display:none"' : ''}>+ Tambah Gambar</button>
            <input type="file" id="reportImgInput" accept="image/jpeg,image/png,image/jpg,image/webp" style="display:none" onchange="handleReportImageUpload(this)">
        </div>`;
    }

    if (data.ready_to_save) {
        const remindMsg = currentLang === 'en'
            ? '⚠️ Please review the generated document carefully before downloading. Ensure all information is accurate and complete.'
            : '⚠️ Sila semak semula dokumen yang telah dijana sebelum dimuat turun. Pastikan semua maklumat adalah tepat dan lengkap.';
        html += `<div class="doc-review-reminder">${remindMsg}</div>`;
        html += '<div class="doc-actions">';
        html += `<button class="doc-action-btn download-btn" onclick="downloadDocument()">\u{1F4E5} Muat Turun (.docx)</button>`;
        html += '</div>';
    }

    html += '</div>';
    return html;
}

function renderAutoReviewPanel(review) {
    const score = review.score || '?';
    const scoreClass = {'A': 'score-a', 'B': 'score-b', 'C': 'score-c', 'D': 'score-d'}[score] || 'score-b';
    const issues = review.issues || [];
    const mandatory = issues.filter(i => i.severity === 'WAJIB_BETULKAN');
    const improvement = review.improvement || null;

    let html = `<div class="auto-review-panel">
        <div class="auto-review-header">
            <span class="auto-review-title">📝 Semakan & Penambahbaikan Automatik</span>
            <span class="review-score ${scoreClass}">${score}</span>
        </div>
        <p class="auto-review-summary">${escapeHtml(review.summary || review.message || '')}</p>`;

    // Show what was improved
    if (improvement) {
        const applied = improvement.changes_applied || [];
        const skipped = improvement.changes_skipped || [];
        const needsInfo = improvement.needs_info;

        if (applied.length > 0) {
            html += `<div class="review-issues-group"><div class="review-group-label improved-label">✅ Telah Diperbaiki (${applied.length})</div>`;
            applied.forEach(change => {
                html += `<div class="review-issue improved-issue"><span class="issue-text">${escapeHtml(change)}</span></div>`;
            });
            html += '</div>';
        }

        // Senarai diskip disembunyikan — bekerja di belakang tabir

        if (needsInfo) {
            html += `<div class="review-needs-info">
                <span class="needs-info-icon">❓</span>
                <span class="needs-info-text">${escapeHtml(needsInfo)}</span>
                <button class="needs-info-reply-btn" onclick="replyNeedsInfo(${JSON.stringify(needsInfo)})">Balas</button>
            </div>`;
        }

        if (applied.length === 0 && skipped.length === 0 && !needsInfo) {
            html += `<div class="review-all-good">✅ Dokumen sudah baik, tiada penambahbaikan diperlukan.</div>`;
        }
    } else if (issues.length === 0) {
        html += `<div class="review-all-good">✅ ${escapeHtml(review.message || 'Dokumen dalam keadaan baik.')}</div>`;
    }

    // Show remaining mandatory issues (not auto-fixable)
    if (mandatory.length > 0) {
        html += `<div class="review-issues-group"><div class="review-group-label mandatory-label">⚠️ Masih Perlu Perhatian (${mandatory.length})</div>`;
        mandatory.forEach((issue, idx) => {
            const fixPrompt = issue.suggestion
                ? `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.suggestion}`
                : `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.issue || ''}`;
            html += `<div class="review-issue mandatory-issue">
                <span class="issue-location">${escapeHtml(issue.location || '')}</span>
                <span class="issue-text">${escapeHtml(issue.issue || '')}</span>
                ${issue.suggestion ? `<span class="issue-suggestion">💡 ${escapeHtml(issue.suggestion)}</span>` : ''}
                <button class="issue-fix-btn" data-prompt="${escapeAttr(fixPrompt)}" onclick="fixLetterIssue(this)">🔧 Betulkan</button>
            </div>`;
        });
        html += '</div>';
    }

    html += '</div>';
    return html;
}

function replyNeedsInfo(question) {
    const input = document.getElementById('chatInput');
    if (input) {
        input.focus();
        input.placeholder = question;
    }
}

let _pendingFixBtn = null;
let _pendingFixMsgDiv = null;
let _pendingLetterFixBtn = null;
let _pendingLetterMsgDiv = null;
let _suppressUserMsg = false;
let _undoReviewState = null;
let _undoLetterState = null;
let _activeLetterMsgDiv = null; // tracks the active letter/report message for in-place updates

function fixReviewIssue(btn) {
    const prompt = btn.dataset.prompt;
    if (!prompt) return;
    btn.textContent = '⏳ Sedang diproses...';
    btn.disabled = true;
    btn.classList.add('fix-processing');
    _pendingFixBtn = btn;
    _pendingFixMsgDiv = btn.closest('.message');
    _suppressUserMsg = true;
    const input = document.getElementById('chatInput');
    if (!input) return;
    input.value = prompt;
    input.dispatchEvent(new Event('input'));
    input.focus();
    document.getElementById('sendBtn')?.click();
}

function fixLetterIssue(btn) {
    const prompt = btn.dataset.prompt;
    if (!prompt) return;
    btn.textContent = '⏳ Sedang diproses...';
    btn.disabled = true;
    btn.classList.add('fix-processing');
    _pendingLetterFixBtn = btn;
    _pendingLetterMsgDiv = btn.closest('.message');
    _suppressUserMsg = true;
    const input = document.getElementById('chatInput');
    if (!input) return;
    input.value = prompt;
    input.dispatchEvent(new Event('input'));
    input.focus();
    document.getElementById('sendBtn')?.click();
}

function undoReviewFix() {
    if (!_undoReviewState) return;
    const { msgDiv, content } = _undoReviewState;
    const previewEl = msgDiv.querySelector('#reviewDocPreview');
    if (previewEl) previewEl.textContent = content;
    saveDocumentEdits(content);
    msgDiv.querySelector('.undo-fix-btn')?.remove();
    _undoReviewState = null;
    showToast('Pembetulan telah dibatalkan.', true);
}

function undoLetterFix() {
    if (!_undoLetterState) return;
    const { msgDiv, content, htmlContent } = _undoLetterState;
    const previewEl = msgDiv.querySelector('#docPreview');
    const previewHtmlEl = msgDiv.querySelector('#docPreviewHtml');
    if (previewEl) previewEl.textContent = content;
    if (previewHtmlEl && htmlContent) previewHtmlEl.innerHTML = htmlContent;
    msgDiv.querySelector('.undo-fix-btn')?.remove();
    _undoLetterState = null;
    showToast('Pembetulan telah dibatalkan.', true);
}

// ═══ Report image upload ═══

async function triggerReportImageUpload() {
    document.getElementById('reportImgInput')?.click();
}

async function handleReportImageUpload(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = async () => {
            if (img.naturalWidth <= img.naturalHeight) {
                showToast('Gambar mesti landscape (lebar > tinggi). Sila pilih gambar landscape.', false);
                input.value = '';
                return;
            }
            const fd = new FormData();
            fd.append('file', file);
            fd.append('session_id', sessionId);
            try {
                const res = await fetch('/api/report/upload-image', { method: 'POST', body: fd });
                const result = await res.json();
                if (result.ok) {
                    showToast(`Gambar ${result.count}/${result.max} berjaya dimuat naik.`, true);
                    await _refreshReportImages();
                } else {
                    showToast(result.error || 'Gagal muat naik gambar.', false);
                }
            } catch (_) { showToast('Gagal muat naik gambar.', false); }
            input.value = '';
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function _refreshReportImages() {
    try {
        const res = await fetch(`/api/report/images?session_id=${encodeURIComponent(sessionId)}`);
        const data = await res.json();
        const images = data.images || [];
        const grid = document.getElementById('reportImgGrid');
        const counter = document.getElementById('reportImgCounter');
        const addBtn = document.getElementById('reportImgAddBtn');
        if (grid) {
            grid.innerHTML = images.map((img, i) => `
                <div class="report-img-thumb">
                    <img src="${img.url}" alt="Gambar ${i + 1}">
                    <button class="report-img-remove" onclick="removeReportImage(${i})" title="Buang gambar">✕</button>
                </div>`).join('');
        }
        if (counter) counter.textContent = images.length;
        if (addBtn) addBtn.style.display = images.length >= (data.max || 4) ? 'none' : 'inline-flex';
    } catch (_) {}
}

async function removeReportImage(index) {
    try {
        const res = await fetch(`/api/report/image/${index}?session_id=${encodeURIComponent(sessionId)}`, { method: 'DELETE' });
        const result = await res.json();
        if (result.ok) await _refreshReportImages();
        else showToast('Gagal membuang gambar.', false);
    } catch (_) {}
}

// ═══ Document actions ═══

async function downloadReviewDocument() {
    const preview = document.getElementById('reviewDocPreview');
    if (preview) await saveDocumentEdits(preview.innerText);
    try {
        const res = await fetch(`/api/document/download?session_id=${encodeURIComponent(sessionId)}`);
        if (!res.ok) throw new Error('Gagal memuat turun dokumen.');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cd = res.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename="?([^"]+)"?/);
        a.download = match ? match[1] : 'dokumen_diperbetulkan.docx';
        a.click(); URL.revokeObjectURL(url);
    } catch (err) { alert(err.message); }
}

async function downloadDocument() {
    const preview = document.getElementById('docPreview');
    if (preview) await saveDocumentEdits(preview.innerText);
    const endpoint = currentAgent === 'report_generator' ? '/api/report/download' : '/api/document/download';
    try {
        const res = await fetch(`${endpoint}?session_id=${encodeURIComponent(sessionId)}`);
        if (!res.ok) throw new Error('Gagal memuat turun dokumen.');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const cd = res.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename="?([^"]+)"?/);
        a.download = match ? match[1] : 'dokumen_rasmi.docx';
        a.click(); URL.revokeObjectURL(url);
    } catch (err) { alert(err.message); }
}

async function saveDocumentEdits(content) {
    const endpoint = currentAgent === 'report_generator' ? '/api/report/save' : '/api/document/save';
    try {
        await fetch(endpoint, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, content }),
        });
    } catch (_) {}
}

function showEmailDialog() {
    const preview = document.getElementById('docPreview');
    if (preview) saveDocumentEdits(preview.innerText);

    const overlay = document.createElement('div');
    overlay.className = 'email-dialog-overlay';
    overlay.innerHTML = `<div class="email-dialog">
        <h3>\u{1F4E7} Hantar Dokumen Melalui Emel</h3>
        <div class="email-field"><label>Emel Penerima</label><input type="email" id="emailTo" placeholder="contoh@email.com"></div>
        <div class="email-field"><label>Subjek</label><input type="text" id="emailSubject" placeholder="Subjek emel"></div>
        <div class="email-dialog-actions">
            <button class="email-cancel-btn" onclick="this.closest('.email-dialog-overlay').remove()">Batal</button>
            <button class="email-send-btn" onclick="confirmSendEmail()">Hantar</button>
        </div>
    </div>`;
    document.body.appendChild(overlay);
    document.getElementById('emailTo').focus();
}

async function confirmSendEmail() {
    const to = document.getElementById('emailTo').value.trim();
    const subject = document.getElementById('emailSubject').value.trim();
    if (!to) { showToast('Sila masukkan emel penerima.', false); return; }
    const endpoint = currentAgent === 'report_generator' ? '/api/report/send-email' : '/api/document/send-email';
    try {
        const res = await fetch(endpoint, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, to_email: to, subject: subject || 'Dokumen SMARTAssist Hub' }),
        });
        const data = await res.json();
        showToast(data.ok ? (data.message || 'Emel berjaya dihantar.') : (data.error || 'Gagal menghantar emel.'), data.ok);
    } catch (err) { showToast('Ralat: ' + err.message, false); }
    document.querySelector('.email-dialog-overlay')?.remove();
}

function showToast(msg, ok = true) {
    let t = document.getElementById('appToast');
    if (!t) {
        t = document.createElement('div');
        t.id = 'appToast';
        t.className = 'app-toast';
        document.body.appendChild(t);
    }
    t.textContent = msg;
    t.className = `app-toast ${ok ? 'toast-ok' : 'toast-err'}`;
    t.classList.add('show');
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.remove('show'), 3500);
}

// ═══ Chart ═══

function renderChart(container, chartConfig) {
    const canvasEl = container.querySelector('canvas');
    if (!canvasEl) return;
    new Chart(canvasEl.getContext('2d'), {
        type: chartConfig.type || 'bar',
        data: {
            labels: chartConfig.labels || [],
            datasets: (chartConfig.datasets || []).map(ds => ({
                label: ds.label || '', data: ds.data || [],
                backgroundColor: ds.backgroundColor || '#3b82f6',
                borderColor: ds.borderColor || 'transparent', borderWidth: ds.borderWidth || 1,
            })),
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                title: { display: !!chartConfig.title, text: chartConfig.title || '', color: '#f1f5f9', font: { size: 14, weight: 'bold' } },
                legend: { labels: { color: '#94a3b8', font: { size: 12 }, usePointStyle: true } },
                tooltip: { backgroundColor: '#1e293b', titleColor: '#f1f5f9', bodyColor: '#94a3b8', borderColor: '#334155', borderWidth: 1, padding: 10, cornerRadius: 8 },
            },
            scales: chartConfig.type === 'pie' || chartConfig.type === 'doughnut' ? {} : {
                x: { ticks: { color: '#94a3b8', maxRotation: 45 }, grid: { color: '#334155' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' }, beginAtZero: true },
            },
            animation: { duration: 800, easing: 'easeOutQuart' },
        },
    });
}

function toggleChartSize(btn) {
    const wrapper = btn.closest('.da-chart-wrapper');
    // container may have been moved to body — use stored ref or find it
    const container = wrapper._expandedContainer || wrapper.querySelector('.da-chart-container');
    const expanded = !wrapper.classList.contains('expanded');
    wrapper.classList.toggle('expanded', expanded);

    let overlay = document.querySelector('.chart-overlay');
    if (!overlay) { overlay = document.createElement('div'); overlay.className = 'chart-overlay'; document.body.appendChild(overlay); }

    if (expanded) {
        // Store reference before moving
        wrapper._expandedContainer = container;
        wrapper._placeholder = document.createComment('chart-placeholder');
        container.before(wrapper._placeholder);
        document.body.appendChild(container);
        container.style.cssText = `
            position:fixed; top:50vh; left:50vw;
            transform:translate(-50%,-50%);
            width:92vw; height:82vh; z-index:1001;
            background:#ffffff; border-radius:16px;
            padding:28px 32px; border:1px solid #cbd5e1;
            box-shadow:0 24px 64px rgba(0,0,0,0.7);
        `;
        const closeBtn = document.createElement('button');
        closeBtn.id = 'chartCloseBtn';
        closeBtn.innerHTML = '✕';
        closeBtn.style.cssText = `
            position:absolute; top:12px; right:14px;
            background:#f1f5f9; border:1px solid #cbd5e1;
            border-radius:50%; width:32px; height:32px;
            font-size:16px; cursor:pointer; color:#475569;
            display:flex; align-items:center; justify-content:center;
            z-index:1002; line-height:1;
        `;
        closeBtn.onmouseover = () => { closeBtn.style.background = '#e2e8f0'; closeBtn.style.color = '#0f172a'; };
        closeBtn.onmouseout  = () => { closeBtn.style.background = '#f1f5f9'; closeBtn.style.color = '#475569'; };
        closeBtn.onclick = (e) => { e.stopPropagation(); toggleChartSize(btn); };
        container.appendChild(closeBtn);

        overlay.classList.add('active');
        const collapse = () => { toggleChartSize(btn); overlay.removeEventListener('click', collapse); };
        overlay.addEventListener('click', collapse);
    } else {
        // Return container to original position using stored reference
        container.style.cssText = '';
        const closeBtn = document.getElementById('chartCloseBtn');
        if (closeBtn) closeBtn.remove();
        if (wrapper._placeholder) { wrapper._placeholder.replaceWith(container); wrapper._placeholder = null; }
        wrapper._expandedContainer = null;
        overlay.classList.remove('active');
    }
    // Pass the container directly since it may have moved to body
    recolorChart(container, expanded);
}

function recolorChart(container, expanded) {
    const canvasEl = container.querySelector('canvas');
    if (!canvasEl) return;
    const chartInstance = Chart.getChart(canvasEl);
    if (!chartInstance) return;
    const txtColor   = expanded ? '#1e293b' : '#94a3b8';
    const titleColor = expanded ? '#0f172a' : '#f1f5f9';
    const gridColor  = expanded ? '#e2e8f0' : '#334155';
    chartInstance.canvas.style.background = expanded ? '#ffffff' : 'transparent';
    chartInstance.options.plugins.title.color = titleColor;
    chartInstance.options.plugins.title.font = { size: expanded ? 18 : 14, weight: 'bold' };
    chartInstance.options.plugins.legend.labels.color = txtColor;
    chartInstance.options.plugins.legend.labels.font = { size: expanded ? 14 : 12 };
    chartInstance.options.layout = { padding: { top: expanded ? 16 : 4, bottom: expanded ? 70 : 8, left: expanded ? 8 : 0, right: expanded ? 16 : 0 } };
    if (chartInstance.options.scales.x) {
        chartInstance.options.scales.x.ticks.color = txtColor;
        chartInstance.options.scales.x.ticks.font = { size: expanded ? 12 : 11 };
        chartInstance.options.scales.x.ticks.maxRotation = expanded ? 60 : 45;
        chartInstance.options.scales.x.ticks.autoSkip = !expanded;
        chartInstance.options.scales.x.ticks.autoSkipPadding = expanded ? 4 : 10;
        chartInstance.options.scales.x.grid.color = gridColor;
    }
    if (chartInstance.options.scales.y) {
        chartInstance.options.scales.y.ticks.color = txtColor;
        chartInstance.options.scales.y.ticks.font = { size: expanded ? 13 : 11 };
        chartInstance.options.scales.y.grid.color = gridColor;
    }
    chartInstance.update();
}

// ═══ Export ═══

async function downloadAnalysis(format) {
    if (!lastStructuredData) return;
    if (format === 'csv') {
        const table = lastStructuredData.table;
        if (!table) { alert('Tiada jadual untuk dimuat turun.'); return; }
        let csv = '﻿' + table.headers.join(',') + '\n';
        table.rows.forEach(row => { csv += row.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',') + '\n'; });
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'data.csv'; a.click();
        return;
    }
    let chartImage = null;
    const chartCanvas = document.querySelector('.da-chart-container canvas');
    if (chartCanvas) { try { chartImage = chartCanvas.toDataURL('image/png'); } catch (_) {} }
    try {
        const res = await fetch('/api/analysis/export', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, format, data: lastStructuredData, chart_image: chartImage }),
        });
        if (!res.ok) throw new Error('Gagal menjana fail.');
        const blob = await res.blob();
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
        a.download = format === 'pptx' ? 'analisis_data.pptx' : 'analisis_data.pdf'; a.click();
    } catch (err) { alert(err.message); }
}

// ═══ Table tools ═══

function filterTable(tblId, query) {
    const tbl = document.getElementById(tblId);
    if (!tbl) return;
    const rows = tbl.querySelectorAll('tbody tr');
    const q = query.toLowerCase();
    rows.forEach(r => { r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none'; });
}

function sortTable(tblId, colIdx) {
    const tbl = document.getElementById(tblId);
    if (!tbl) return;
    const tbody = tbl.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const th = tbl.querySelectorAll('th')[colIdx];
    const asc = th.dataset.sortDir !== 'asc';
    tbl.querySelectorAll('th').forEach(h => { h.dataset.sortDir = ''; h.querySelector('.sort-icon').textContent = '\u{21C5}'; });
    th.dataset.sortDir = asc ? 'asc' : 'desc';
    th.querySelector('.sort-icon').textContent = asc ? '\u{2191}' : '\u{2193}';
    rows.sort((a, b) => {
        const av = a.cells[colIdx]?.textContent?.trim() || '';
        const bv = b.cells[colIdx]?.textContent?.trim() || '';
        const an = parseFloat(av), bn = parseFloat(bv);
        if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
    });
    rows.forEach(r => tbody.appendChild(r));
}

function downloadTableCSV(tblId) {
    const tbl = document.getElementById(tblId);
    if (!tbl) return;
    const headers = Array.from(tbl.querySelectorAll('th')).map(th => th.textContent.replace(/[⇅↑↓]/g, '').trim());
    const rows = Array.from(tbl.querySelectorAll('tbody tr')).filter(r => r.style.display !== 'none');
    let csv = '﻿' + headers.join(',') + '\n';
    rows.forEach(r => { csv += Array.from(r.cells).map(c => `"${c.textContent.replace(/"/g, '""')}"`).join(',') + '\n'; });
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'jadual.csv'; a.click();
}

// ═══ Utilities ═══

function escapeHtml(text) {
    const div = document.createElement('div'); div.textContent = text; return div.innerHTML;
}

function escapeAttr(text) {
    return text.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function setProcessing(state) {
    isProcessing = state;
    sendBtn.disabled = state;
    chatInput.disabled = state;
    if (uploadBtn) uploadBtn.disabled = state;
    typingIndicator.className = state ? 'typing-indicator active' : 'typing-indicator';
    if (!state) chatInput.focus();
}

// ═══ File Upload ═══

uploadBtn.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    if (currentAgent === 'document_reviewer') {
        await handleReviewUpload(file);
    } else {
        await handleDataUpload(file);
    }
    fileInput.value = '';
});

async function handleDataUpload(file) {
    setProcessing(true);
    addMessage(`Memuat naik fail: ${file.name}...`, 'user');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.ok) {
            hasUploadedData = true;
            uploadBtn.classList.add('has-file');
            fileIndicator.style.display = 'flex';
            fileIndicatorText.textContent = `\u{1F4C4} ${data.filename} (${data.rows} baris, ${data.columns} lajur)`;
            addMessage('', 'assistant', '\u{1F4CA}', 'Analisis Data', {
                response_type: 'papar',
                message: `Fail '${data.filename}' berjaya dimuat naik. ${data.rows} baris dan ${data.columns} lajur dikesan.`,
                penemuan: [`Lajur: ${data.column_names.join(', ')}`],
                susulan: ['Tunjukkan ringkasan statistik', 'Paparkan 10 baris pertama', 'Buat carta berdasarkan data ini'],
            });
        } else {
            addMessage(data.error || 'Gagal memuat naik fail.', 'assistant', '\u{26A0}\u{FE0F}', 'Sistem');
        }
    } catch (err) {
        addMessage(`Ralat muat naik: ${err.message}`, 'assistant', '\u{26A0}\u{FE0F}', 'Sistem');
    } finally { setProcessing(false); }
}

async function handleReviewUpload(file) {
    setProcessing(true);
    addMessage(`📎 Memuat naik: ${file.name}`, 'user');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    try {
        const res = await fetch('/api/review/upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.ok) {
            uploadBtn.classList.add('has-file');
            fileIndicator.style.display = 'flex';
            fileIndicatorText.textContent = `📄 ${data.filename} (${data.doc_type}, ${data.char_count} aksara)`;
            // Auto-trigger review
            canvasWelcome.style.display = 'none';
            await sendReviewRequest(file.name, data.doc_type);
        } else {
            addMessage(data.error || 'Gagal memuat naik fail.', 'assistant', '⚠️', 'Sistem');
        }
    } catch (err) {
        addMessage(`Ralat muat naik: ${err.message}`, 'assistant', '⚠️', 'Sistem');
    } finally { setProcessing(false); }
}

async function sendReviewRequest(filename, docType) {
    const reviewMsg = currentLang === 'bm'
        ? `Sila semak dokumen "${filename}" yang telah dimuat naik.`
        : `Please review the uploaded document "${filename}".`;

    setProcessing(true);
    typingIndicator.classList.add('active');
    canvasMessages.scrollTop = canvasMessages.scrollHeight;

    try {
        const res = await fetch('/api/agent-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: reviewMsg, session_id: sessionId, agent: 'document_reviewer' }),
        });
        const result = await res.json();
        typingIndicator.classList.remove('active');
        const info = getAgentInfo('document_reviewer');
        let structured = null;
        try { structured = JSON.parse(result.response); } catch (_) {}
        addMessage(result.response, 'assistant', info.icon, info.name, structured);
    } catch (err) {
        typingIndicator.classList.remove('active');
        addMessage(`Ralat: ${err.message}`, 'assistant', '⚠️', 'Sistem');
    } finally { setProcessing(false); }
}

fileRemoveBtn.addEventListener('click', () => {
    hasUploadedData = false;
    uploadBtn.classList.remove('has-file');
    fileIndicator.style.display = 'none';
});

// ═══ Chat Send ═══

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || isProcessing) return;
    chatInput.value = '';
    chatInput.style.height = 'auto';
    if (!_suppressUserMsg) addMessage(message, 'user');
    _suppressUserMsg = false;
    setProcessing(true);

    try {
        const endpoint = currentAgent ? '/api/agent-chat' : '/api/chat';
        const body = currentAgent
            ? { message, session_id: sessionId, agent: currentAgent, lang: currentLang }
            : { message, session_id: sessionId, lang: currentLang };
        const res = await fetch(endpoint, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        lastActiveAgent = data.agent || currentAgent || 'fallback';
        addMessage(data.response, 'assistant', data.agent_icon, data.agent_name, data.structured);
    } catch (err) {
        addMessage(`Ralat: ${err.message}. Sila cuba lagi.`, 'assistant', '\u{26A0}\u{FE0F}', 'Sistem');
    } finally { setProcessing(false); }
}

function useQuickAction(text) {
    chatInput.value = text;
    sendMessage();
}

// ═══ Event Listeners ═══

sendBtn.addEventListener('click', sendMessage);
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
});

document.getElementById('backBtn').addEventListener('click', goHome);
document.getElementById('canvasNewBtn').addEventListener('click', newSession);
document.getElementById('canvasHistoryBtn').addEventListener('click', toggleHistory);
document.getElementById('historyBtn').addEventListener('click', toggleHistory);
document.getElementById('historyCloseBtn').addEventListener('click', toggleHistory);
historyOverlay.addEventListener('click', toggleHistory);
document.getElementById('langToggle').addEventListener('click', toggleLanguage);
applyLanguage(currentLang);

// Agent cards
document.querySelectorAll('.agent-card').forEach(card => {
    card.addEventListener('click', () => openAgent(card.dataset.agent));
});

// ═══════════════════════════════════════
//  LETTERHEAD SETTINGS PAGE
// ═══════════════════════════════════════

let _lhActiveTab = 'letterhead';

let _lhReturnToCanvas = false;

function openLhPage() {
    _lhReturnToCanvas = false;
    landingPage.style.display = 'none';
    agentCanvas.style.display = 'none';
    document.getElementById('lhPage').style.display = 'flex';
    loadLhList();
}

function showLetterheadPage() {
    _lhReturnToCanvas = true;
    agentCanvas.style.display = 'none';
    landingPage.style.display = 'none';
    document.getElementById('lhPage').style.display = 'flex';
    loadLhList();
}

function closeLhPage() {
    document.getElementById('lhPage').style.display = 'none';
    if (_lhReturnToCanvas) {
        agentCanvas.style.display = 'flex';
    } else {
        landingPage.style.display = '';
    }
}

function switchLhTab(tab) {
    _lhActiveTab = tab;
    document.querySelectorAll('.lh-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    document.querySelectorAll('.lh-tab-panel').forEach(p => p.classList.toggle('active', p.id === `lhPanel-${tab}`));
}

async function loadLhList() {
    try {
        const res = await fetch('/api/letterhead/list');
        const data = await res.json();
        renderLhGrid('letterhead', data.letterheads.filter(lh => lh.type === 'letterhead'), data.active_letterhead_id);
        renderLhGrid('logo', data.letterheads.filter(lh => lh.type === 'logo'), data.active_logo_id);
    } catch (_) {}
}

function renderLhGrid(lhType, letterheads, activeId) {
    const dict = I18N[currentLang];
    const grid = document.getElementById(`lhGrid-${lhType}`);
    const notice = document.getElementById(`lhActiveNotice-${lhType}`);
    const label = document.getElementById(`lhActiveLabel-${lhType}`);
    if (!grid) return;

    if (letterheads.length === 0) {
        grid.innerHTML = `<div class="lh-empty">${dict.lh_empty}</div>`;
        if (notice) notice.style.display = 'none';
        return;
    }

    const active = letterheads.find(lh => lh.id === activeId);
    if (active && notice) {
        notice.style.display = 'flex';
        label.textContent = `${dict.lh_active_label}: ${active.name}`;
    } else if (notice) {
        notice.style.display = 'none';
    }

    grid.innerHTML = letterheads.map(lh => {
        const isActive = lh.id === activeId;
        const date = new Date(lh.uploaded).toLocaleDateString('ms-MY', { day: '2-digit', month: 'short', year: 'numeric' });
        return `<div class="lh-card ${isActive ? 'active' : ''}" id="lhcard-${lh.id}">
            <div class="lh-card-preview">
                <img src="/api/letterhead/image/${encodeURIComponent(lh.filename)}" alt="${escapeHtml(lh.name)}" loading="lazy">
            </div>
            <div class="lh-card-body">
                ${isActive ? `<div class="lh-card-active-badge">✓ ${dict.lh_selected}</div>` : ''}
                <input class="lh-card-name-input" value="${escapeHtml(lh.name)}"
                    onblur="lhRename('${lh.id}', this.value)"
                    onkeydown="if(event.key==='Enter'){this.blur();}">
                <div class="lh-card-meta">${date}</div>
                <div class="lh-card-actions">
                    <button class="lh-card-select-btn ${isActive ? 'selected' : ''}"
                        onclick="lhSelect('${lh.id}','${lhType}')"
                        ${isActive ? 'disabled' : ''}>
                        ${isActive ? dict.lh_selected : dict.lh_select}
                    </button>
                    <button class="lh-card-delete-btn" onclick="lhDelete('${lh.id}')">${dict.lh_delete}</button>
                </div>
            </div>
        </div>`;
    }).join('');
}

async function lhSelect(id, lhType) {
    await fetch('/api/letterhead/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, lh_type: lhType }),
    });
    loadLhList();
}

async function lhDelete(id) {
    if (!confirm(currentLang === 'bm' ? 'Padam imej ini?' : 'Delete this image?')) return;
    await fetch(`/api/letterhead/${encodeURIComponent(id)}`, { method: 'DELETE' });
    loadLhList();
}

async function lhRename(id, name) {
    if (!name.trim()) return;
    await fetch('/api/letterhead/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name: name.trim() }),
    });
    loadLhList();
}

function showLhToast(msg, ok = true) {
    let t = document.getElementById('lhToast');
    if (!t) {
        t = document.createElement('div');
        t.id = 'lhToast';
        t.className = 'lh-toast';
        document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.borderColor = ok ? 'var(--green)' : 'var(--red)';
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

async function uploadLhFiles(files, lhType) {
    const dict = I18N[currentLang];
    for (const file of files) {
        if (file.size > 5 * 1024 * 1024) {
            showLhToast(`${file.name}: fail terlalu besar (maks 5 MB)`, false);
            continue;
        }
        const fd = new FormData();
        fd.append('file', file);
        fd.append('label', file.name.replace(/\.[^.]+$/, ''));
        fd.append('lh_type', lhType);
        try {
            const res = await fetch('/api/letterhead/upload', { method: 'POST', body: fd });
            const data = await res.json();
            showLhToast(data.ok ? dict.lh_upload_success : (data.error || dict.lh_upload_fail), data.ok);
        } catch (_) {
            showLhToast(dict.lh_upload_fail, false);
        }
    }
    loadLhList();
}

// Wire up each tab's drop zone and file input
['letterhead', 'logo'].forEach(lhType => {
    const dz = document.getElementById(`lhDropZone-${lhType}`);
    const fi = document.getElementById(`lhFileInput-${lhType}`);
    if (!dz || !fi) return;
    dz.addEventListener('click', e => { if (!e.target.closest('button')) fi.click(); });
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('dragover'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
    dz.addEventListener('drop', e => {
        e.preventDefault(); dz.classList.remove('dragover');
        if (e.dataTransfer.files.length) uploadLhFiles(Array.from(e.dataTransfer.files), lhType);
    });
    fi.addEventListener('change', () => {
        if (fi.files.length) uploadLhFiles(Array.from(fi.files), lhType);
        fi.value = '';
    });
    const btn = dz.querySelector('[data-trigger]');
    if (btn) btn.addEventListener('click', e => { e.stopPropagation(); fi.click(); });
});

// Tab switching
document.querySelectorAll('.lh-tab').forEach(tab => {
    tab.addEventListener('click', () => switchLhTab(tab.dataset.tab));
});

document.getElementById('lhSettingsBtn')?.addEventListener('click', openLhPage);
document.getElementById('lhBackBtn').addEventListener('click', closeLhPage);
document.getElementById('adminBtn').addEventListener('click', openAdminPage);
document.getElementById('adminBackBtn').addEventListener('click', closeAdminPage);
document.getElementById('adminRefreshBtn').addEventListener('click', loadAdminStats);

// ═══════════════════════════════════════
//  WORD-LIKE PREVIEW MODAL
// ═══════════════════════════════════════

async function openWordPreview() {
    const previewHtml = document.getElementById('docPreviewHtml');
    const preview = document.getElementById('docPreview');
    const isHtmlMode = !!previewHtml;

    // Fetch active letterhead for current agent
    const lhType = currentAgent === 'report_generator' ? 'logo' : 'letterhead';
    let lhImgHtml = '';
    try {
        const r = await fetch(`/api/letterhead/active?lh_type=${lhType}`);
        const d = await r.json();
        if (d.active) {
            lhImgHtml = `<div class="word-page-letterhead">
                <img src="/api/letterhead/image/${encodeURIComponent(d.active.filename)}" alt="letterhead">
            </div><hr class="word-page-divider">`;
        }
    } catch (_) {}

    let pagesHtml;
    if (isHtmlMode) {
        // HTML preview already contains logo/letterhead — no need to add again
        pagesHtml = `<div class="word-page" style="position:relative"><div class="word-page-html-content">${previewHtml.innerHTML}</div></div>`;
    } else {
        if (!preview) return;
        const text = preview.innerText || preview.textContent;
        const pages = _paginateWordContent(text, !!lhImgHtml);
        const totalPages = pages.length;
        pagesHtml = pages.map((pageText, i) => {
            const lh = i === 0 ? lhImgHtml : '';
            const editable = i === 0 ? 'contenteditable="true" id="wordPreviewText"' : '';
            const pageNum = totalPages > 1
                ? `<div class="word-page-num">${i + 1} / ${totalPages}</div>` : '';
            return `<div class="word-page" style="position:relative">${lh}<pre ${editable} spellcheck="false">${escapeHtml(pageText)}</pre>${pageNum}</div>`;
        }).join('');
    }

    const dict = I18N[currentLang];
    const overlay = document.createElement('div');
    overlay.className = 'word-preview-overlay';
    overlay.id = 'wordPreviewOverlay';
    overlay.innerHTML = `
        <div class="word-preview-toolbar">
            <div class="word-preview-title">📄 ${dict.word_preview}</div>
            <div class="word-preview-actions">
                <button class="word-preview-dl-btn" onclick="downloadDocument()">📥 ${currentLang === 'bm' ? 'Muat Turun .docx' : 'Download .docx'}</button>
                <button class="word-preview-close-btn" onclick="closeWordPreview()">${dict.word_close}</button>
            </div>
        </div>
        <div class="word-preview-scroll">${pagesHtml}</div>`;
    document.body.appendChild(overlay);

    if (!isHtmlMode) {
        const wordText = document.getElementById('wordPreviewText');
        if (wordText && preview) {
            wordText.addEventListener('input', () => {
                preview.innerText = wordText.innerText;
            });
        }
    }
}

function _paginateWordContent(fullText, hasLetterhead) {
    // A4 content area: (297 - 50.8)mm height, (210 - 57.1)mm width at 96dpi (1px ≈ 0.2646mm)
    const MM_TO_PX = 3.7795;
    const contentH = Math.round((297 - 50.8) * MM_TO_PX);   // ~926px
    const contentW = Math.round((210 - 57.1) * MM_TO_PX);   // ~578px
    const letterheadH = hasLetterhead ? 108 : 0;             // approx header + divider

    const measurer = document.createElement('pre');
    Object.assign(measurer.style, {
        position: 'fixed', top: '-9999px', left: '-9999px',
        width: contentW + 'px', visibility: 'hidden', pointerEvents: 'none',
        fontFamily: "'Arial', sans-serif", fontSize: '11pt', lineHeight: '1.5',
        whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        margin: '0', padding: '0', border: 'none', background: 'none',
    });
    document.body.appendChild(measurer);

    const lines = fullText.split('\n');
    const pages = [];
    let current = [];
    let isFirst = true;

    for (let i = 0; i < lines.length; i++) {
        current.push(lines[i]);
        measurer.textContent = current.join('\n');
        const limit = isFirst ? contentH - letterheadH : contentH;
        if (measurer.scrollHeight > limit) {
            current.pop();
            if (current.length > 0) {
                pages.push(current.join('\n'));
                isFirst = false;
                current = [lines[i]];
            } else {
                // Line itself is too long — keep it and continue
                pages.push(lines[i]);
                isFirst = false;
                current = [];
            }
        }
    }
    if (current.length > 0) pages.push(current.join('\n'));
    document.body.removeChild(measurer);
    return pages.length > 0 ? pages : [fullText];
}

function closeWordPreview() {
    document.getElementById('wordPreviewOverlay')?.remove();
}

// ═══════════════════════════════════════
//  ADMIN DASHBOARD
// ═══════════════════════════════════════

let _adminAgentChart = null;
let _adminFeedbackChart = null;

function openAdminPage() {
    landingPage.style.display = 'none';
    document.getElementById('adminPage').style.display = 'flex';
    loadAdminStats();
}

function closeAdminPage() {
    document.getElementById('adminPage').style.display = 'none';
    landingPage.style.display = '';
}

async function loadAdminStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        document.getElementById('statTotalSessions').textContent = data.total_sessions;
        document.getElementById('statTotalMessages').textContent = data.total_messages;
        document.getElementById('statFeedbackUp').textContent = data.feedback_total?.up ?? 0;
        document.getElementById('statFeedbackDown').textContent = data.feedback_total?.down ?? 0;

        const labels = Object.keys(data.agent_counts).map(k => data.agent_labels?.[k] || k);
        const counts = Object.values(data.agent_counts);
        const agentColors = ['#7c3aed', '#d97706', '#16a34a', '#0891b2', '#dc2626', '#6b7280'];

        const agentCtx = document.getElementById('adminAgentChart').getContext('2d');
        if (_adminAgentChart) _adminAgentChart.destroy();
        _adminAgentChart = new Chart(agentCtx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Sesi',
                    data: counts,
                    backgroundColor: agentColors.map(c => c + 'cc'),
                    borderColor: agentColors,
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { backgroundColor: '#1e293b', titleColor: '#f1f5f9', bodyColor: '#94a3b8', padding: 10, cornerRadius: 8 },
                },
                scales: {
                    x: { ticks: { color: '#94a3b8', precision: 0 }, grid: { color: '#1e293b' }, beginAtZero: true, suggestedMax: Math.max(...counts, 5) },
                    y: { ticks: { color: '#e2e8f0', font: { size: 12 } }, grid: { display: false } },
                },
            },
        });

        const fbLabels = Object.keys(data.feedback_by_agent).map(k => data.agent_labels?.[k] || k);
        const fbUp = Object.values(data.feedback_by_agent).map(v => v.up || 0);
        const fbDown = Object.values(data.feedback_by_agent).map(v => v.down || 0);
        const fbCtx = document.getElementById('adminFeedbackChart').getContext('2d');
        if (_adminFeedbackChart) _adminFeedbackChart.destroy();
        _adminFeedbackChart = new Chart(fbCtx, {
            type: 'bar',
            data: {
                labels: fbLabels,
                datasets: [
                    { label: '👍 Positif', data: fbUp, backgroundColor: '#22c55ecc', borderColor: '#22c55e', borderWidth: 2, borderRadius: 6, borderSkipped: false },
                    { label: '👎 Negatif', data: fbDown, backgroundColor: '#ef4444cc', borderColor: '#ef4444', borderWidth: 2, borderRadius: 6, borderSkipped: false },
                ],
            },
            options: {
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#94a3b8', boxWidth: 12, boxHeight: 12, borderRadius: 4 } },
                    tooltip: { backgroundColor: '#1e293b', titleColor: '#f1f5f9', bodyColor: '#94a3b8', padding: 10, cornerRadius: 8 },
                },
                scales: {
                    x: { ticks: { color: '#94a3b8', precision: 0 }, grid: { color: '#1e293b' }, beginAtZero: true, suggestedMax: Math.max(...fbUp, ...fbDown, 5) },
                    y: { ticks: { color: '#e2e8f0', font: { size: 12 } }, grid: { display: false } },
                },
            },
        });

        const tbody = document.querySelector('#adminRecentTable tbody');
        if (tbody) {
            tbody.innerHTML = (data.recent_sessions || []).map(s => {
                const t = s.updated ? new Date(s.updated).toLocaleString('ms-MY', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—';
                const agentName = data.agent_labels?.[s.agent] || s.agent || '—';
                return `<tr>
                    <td title="${escapeHtml(s.session_id)}">${escapeHtml(s.session_id.slice(-8))}</td>
                    <td>${escapeHtml(agentName)}</td>
                    <td title="${escapeHtml(s.title || '')}">${escapeHtml((s.title || '').slice(0, 40))}</td>
                    <td>${s.message_count || 0}</td>
                    <td>${t}</td>
                </tr>`;
            }).join('') || '<tr><td colspan="5" style="color:var(--text-secondary);text-align:center;">Tiada sesi lagi.</td></tr>';
        }
    } catch (e) {
        console.error('Admin stats error:', e);
    }
}
