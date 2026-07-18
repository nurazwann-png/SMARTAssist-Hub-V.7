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
let _awaitingFollowup = false;  // true selepas dokumen siap — tunggu jawapan ya/tidak
let _reviewDocText = null;
let _reviewDocHtml      = null;
let _reviewIsPdf        = false;
let _reviewPdfObjectUrl = null;
let _reviewPdfImages    = [];

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
        profile_title: 'Profil Pengguna',
        profile_nama: 'Nama Penuh', profile_nama_ph: 'Nama seperti dalam kad pengenalan',
        profile_jawatan: 'Jawatan', profile_jawatan_ph: 'cth: Penolong Pegawai Pendidikan',
        profile_stesen: 'Stesen Bertugas', profile_stesen_ph: 'cth: PPD Hulu Langat',
        profile_daerah: 'Daerah', profile_daerah_ph: 'cth: Hulu Langat',
        profile_negeri: 'Negeri', profile_negeri_ph: '— Pilih Negeri —',
        profile_save: 'Simpan Profil', profile_logout: 'Log Keluar',
        profile_dashboard: 'Papan Pemuka Penggunaan',
        profile_saved_ok: '✓ Profil berjaya disimpan', profile_saved_fail: 'Gagal menyimpan. Cuba semula.',
        profile_conn_err: 'Ralat sambungan.',
        // Canvas chrome
        work_panel_title: 'Ruang Kerja',
        work_panel_empty: 'Borang dan pratonton dokumen yang dijana ejen akan dipaparkan di sini.',
        canvas_history_tip: 'Sejarah', canvas_new_tip: 'Sesi Baharu', canvas_lh_tip: 'Kepala Surat & Logo',
        // Upload button tooltips
        upload_tip_reviewer: 'Muat naik PDF atau Word untuk semakan',
        upload_tip_letter: 'Muat naik PDF untuk jana surat iringan',
        upload_tip_data: 'Muat naik fail CSV/Excel',
        // Feedback buttons
        feedback_pos: 'Berguna', feedback_neg: 'Tidak berguna',
        // History panel
        history_msg_suffix: 'mesej', history_older: 'Sesi Lama',
        history_delete_tip: 'Padam', history_load_fail: 'Gagal memuatkan sejarah.',
        // KPM bubble
        kpm_input_ph: 'Taip soalan anda...', kpm_close_tip: 'Tutup', kpm_avatar_sub: 'Ejen Sokongan KPM',
        // Generic errors
        error_generic: 'Maaf, ralat berlaku. Sila cuba lagi.',
        error_conn: 'Ralat sambungan. Sila cuba lagi.',
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
        profile_title: 'User Profile',
        profile_nama: 'Full Name', profile_nama_ph: 'Name as per identity card',
        profile_jawatan: 'Position', profile_jawatan_ph: 'e.g.: Assistant Education Officer',
        profile_stesen: 'Work Station', profile_stesen_ph: 'e.g.: PPD Hulu Langat',
        profile_daerah: 'District', profile_daerah_ph: 'e.g.: Hulu Langat',
        profile_negeri: 'State', profile_negeri_ph: '— Select State —',
        profile_save: 'Save Profile', profile_logout: 'Log Out',
        profile_dashboard: 'Usage Dashboard',
        profile_saved_ok: '✓ Profile saved successfully', profile_saved_fail: 'Failed to save. Please try again.',
        profile_conn_err: 'Connection error.',
        // Canvas chrome
        work_panel_title: 'Workspace',
        work_panel_empty: 'Forms and document previews generated by the agent will appear here.',
        canvas_history_tip: 'History', canvas_new_tip: 'New Session', canvas_lh_tip: 'Letterhead & Logo',
        // Upload button tooltips
        upload_tip_reviewer: 'Upload PDF or Word for review',
        upload_tip_letter: 'Upload PDF to generate a cover letter',
        upload_tip_data: 'Upload CSV/Excel file',
        // Feedback buttons
        feedback_pos: 'Helpful', feedback_neg: 'Not helpful',
        // History panel
        history_msg_suffix: 'messages', history_older: 'Older Sessions',
        history_delete_tip: 'Delete', history_load_fail: 'Failed to load history.',
        // KPM bubble
        kpm_input_ph: 'Type your question...', kpm_close_tip: 'Close', kpm_avatar_sub: 'KPM Support Agent',
        // Generic errors
        error_generic: 'Sorry, an error occurred. Please try again.',
        error_conn: 'Connection error. Please try again.',
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
    const backBtn = document.getElementById('backBtn');
    if (backBtn) backBtn.textContent = dict.back_btn;

    // Canvas chrome tooltips
    const hBtn = document.getElementById('canvasHistoryBtn');
    if (hBtn) hBtn.title = dict.canvas_history_tip;
    const nBtn = document.getElementById('canvasNewBtn');
    if (nBtn) nBtn.title = dict.canvas_new_tip;
    const lhBtn = document.getElementById('sidebarLhBtn');
    if (lhBtn) lhBtn.title = dict.canvas_lh_tip;

    // Work panel static labels
    const wpTitle = document.querySelector('.work-panel-title');
    if (wpTitle) wpTitle.textContent = dict.work_panel_title;
    const wpEmpty = document.querySelector('.work-panel-empty p');
    if (wpEmpty) wpEmpty.textContent = dict.work_panel_empty;

    // Upload button tooltip (depends on current agent)
    if (typeof currentAgent !== 'undefined' && currentAgent && typeof uploadBtn !== 'undefined' && uploadBtn) {
        if (currentAgent === 'document_reviewer') uploadBtn.title = dict.upload_tip_reviewer;
        else if (currentAgent === 'letter_generator') uploadBtn.title = dict.upload_tip_letter;
        else uploadBtn.title = dict.upload_tip_data;
    }

    // KPM bubble elements
    const kpmInput = document.getElementById('kpmBubbleInput');
    if (kpmInput) kpmInput.placeholder = dict.kpm_input_ph;
    const kpmClose = document.querySelector('.kpm-bubble-close');
    if (kpmClose) kpmClose.title = dict.kpm_close_tip;
    const kpmSub = document.querySelector('.kpm-avatar-sublabel');
    if (kpmSub) kpmSub.textContent = dict.kpm_avatar_sub;
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
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
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
    _awaitingFollowup = false;
    _activeLetterMsgDiv = null;
    _activeWorkItem = null;
    _activeChatBubble = null;
    const _wpContent = document.getElementById('workPanelContent');
    const _wpEmpty = document.getElementById('workPanelEmpty');
    if (_wpContent && _wpEmpty) {
        _wpContent.querySelectorAll('.work-item').forEach(el => el.remove());
        _wpEmpty.style.display = '';
    }
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

    const showUpload = agentKey === 'data_analysis' || agentKey === 'document_reviewer' || agentKey === 'letter_generator';
    uploadBtn.style.display = showUpload ? '' : 'none';
    if (agentKey === 'document_reviewer') {
        fileInput.accept = '.pdf,.docx,.doc';
        uploadBtn.title = I18N[currentLang].upload_tip_reviewer;
    } else if (agentKey === 'letter_generator') {
        fileInput.accept = '.pdf';
        uploadBtn.title = I18N[currentLang].upload_tip_letter;
    } else {
        fileInput.accept = '.csv,.xlsx,.xls';
        uploadBtn.title = I18N[currentLang].upload_tip_data;
    }
    hasUploadedData = false;
    fileIndicator.style.display = 'none';

    // Clear messages, show welcome
    const msgs = canvasMessages.querySelectorAll('.message');
    msgs.forEach(m => m.remove());
    canvasWelcome.style.display = '';

    landingPage.style.display = 'none';
    agentCanvas.style.display = 'flex';
    // Toggle work panel visibility — hidden for agents that only use chat
    const canvasBody = document.getElementById('chatPanel')?.closest('.canvas-body');
    if (canvasBody) {
        if (agentKey === 'kpm_support') canvasBody.classList.add('no-work-panel');
        else canvasBody.classList.remove('no-work-panel');
    }
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
        addMessage('Tidak dapat memuat ejen. Sila cuba lagi.', 'assistant', info.icon, info.name);
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
        const d = I18N[currentLang];
        if (sessions.length === 0) {
            historyList.innerHTML = `<div class="history-empty">${d.history_empty}</div>`;
            return;
        }
        const locale = currentLang === 'en' ? 'en-GB' : 'ms-MY';
        const buildItem = s => {
            const info = s.agent ? getAgentInfo(s.agent) : { icon: '\u{1F4AC}', name: s.agent };
            const time = new Date(s.updated).toLocaleString(locale, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
            return `<div class="history-item" onclick="loadSession('${escapeAttr(s.session_id)}', '${escapeAttr(s.agent)}')">
                <div class="history-item-icon">${info.icon}</div>
                <div class="history-item-info">
                    <div class="history-item-title">${escapeHtml(s.title)}</div>
                    <div class="history-item-meta">${info.name} &middot; ${time} &middot; ${s.message_count} ${d.history_msg_suffix}</div>
                </div>
                <button class="history-item-delete" onclick="event.stopPropagation(); deleteSession('${escapeAttr(s.session_id)}')" title="${d.history_delete_tip}">&times;</button>
            </div>`;
        };
        const recent = sessions.slice(0, 10);
        const older  = sessions.slice(10);
        let html = recent.map(buildItem).join('');
        if (older.length > 0) {
            html += `
            <div class="history-older-toggle" onclick="this.classList.toggle('open')">
                <span class="history-older-icon">🗂️</span>
                <span class="history-older-label">${d.history_older} <span class="history-older-count">${older.length}</span></span>
                <span class="history-older-chevron">›</span>
            </div>
            <div class="history-older-list">
                ${older.map(buildItem).join('')}
            </div>`;
        }
        historyList.innerHTML = html;
    } catch (_) {
        historyList.innerHTML = `<div class="history-empty">${I18N[currentLang].history_load_fail}</div>`;
    }
}

function loadSession(sid, agent) {
    toggleHistory();
    openAgent(agent, sid);
}

async function deleteSession(sid) {
    if (!confirm('Padam sesi ini? Tindakan ini tidak boleh dibatalkan.')) return;
    try {
        await fetch('/api/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sid, message: '' }),
        });
        refreshHistory();
        alert('Sesi telah dipadamkan.');
    } catch (_) {}
}

// ═══ Messages ═══

function addMessage(content, role, agentIcon, agentName, structured) {
    if (canvasWelcome) canvasWelcome.style.display = 'none';

    // ═══ In-place fix intercepts ═══
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
    // ═══ End fix intercepts ═══

    // === Structured content → work panel ===
    const isWorkContent = structured && (
        structured.response_type !== undefined ||
        structured.issues !== undefined ||
        structured.phase !== undefined
    );

    if (isWorkContent) {
        const hasMissing = !!(structured.fields_status?.missing?.length);
        let workHtml;

        if (structured.response_type) {
            lastStructuredData = structured;
            workHtml = buildStructuredHtml(structured);
        } else if (structured.issues !== undefined) {
            workHtml = buildReviewHtml(structured);
        } else {
            workHtml = buildLetterHtml(structured);
        }

        // In-place update for letter/report
        if (structured.phase !== undefined && _activeWorkItem) {
            _activeWorkItem.innerHTML = workHtml;
            if (structured.chart) renderChart(_activeWorkItem, structured.chart);
            if (document.getElementById('reportImgGrid')) _refreshReportImages();
            if (!hasMissing && structured.message && _activeChatBubble) {
                const bbl = _activeChatBubble.querySelector('.message-bubble');
                if (bbl) bbl.innerHTML = escapeHtml(structured.message);
            }
            return;
        }

        // Create work panel item
        const workItem = document.createElement('div');
        workItem.className = 'work-item';
        workItem.innerHTML = workHtml;

        const wpContent = document.getElementById('workPanelContent');
        const wpEmpty = document.getElementById('workPanelEmpty');

        if (structured.phase !== undefined) {
            const prev = wpContent?.querySelector('.work-item[data-letter]');
            if (prev) prev.replaceWith(workItem);
            else { if (wpEmpty) wpEmpty.style.display = 'none'; wpContent?.appendChild(workItem); }
            workItem.dataset.letter = '1';
            _activeWorkItem = workItem;
        } else {
            if (wpEmpty) wpEmpty.style.display = 'none';
            wpContent?.appendChild(workItem);
        }

        if (structured.chart) renderChart(workItem, structured.chart);
        if (document.getElementById('reportImgGrid')) _refreshReportImages();

        // Add agent text to chat panel
        const _rawChatMsg = structured.message || '';
        const chatText = hasMissing ? '' : (_rawChatMsg.trim().startsWith('{') ? '' : _rawChatMsg);
        const chatDiv = document.createElement('div');
        chatDiv.className = `message ${role}`;
        let chatHtml = '';
        if (role === 'assistant' && agentName) {
            chatHtml += `<div class="agent-tag">${agentIcon} ${agentName}</div>`;
        }
        if (chatText) {
            chatHtml += `<div class="message-bubble">${escapeHtml(chatText)}</div>`;
        }
        if (role === 'assistant') {
            const idx = _msgIndex++;
            chatHtml += `<div class="msg-feedback">
                <button class="feedback-btn" id="fb-up-${idx}" onclick="submitFeedback(${idx}, 'up')" title="${I18N[currentLang].feedback_pos}">👍</button>
                <button class="feedback-btn" id="fb-down-${idx}" onclick="submitFeedback(${idx}, 'down')" title="${I18N[currentLang].feedback_neg}">👎</button>
            </div>`;
        }
        chatDiv.innerHTML = chatHtml;
        if (chatHtml.trim()) {
            canvasMessages.insertBefore(chatDiv, typingIndicator);
            canvasMessages.scrollTop = canvasMessages.scrollHeight;
        }
        if (structured.phase !== undefined) _activeChatBubble = chatDiv;
        return;
    }

    // === Plain text → chat panel only ===
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    let html = '';
    if (role === 'assistant' && agentName) {
        html += `<div class="agent-tag">${agentIcon} ${agentName}</div>`;
    }
    html += `<div class="message-bubble">${escapeHtml(content)}</div>`;
    if (role === 'assistant') {
        const idx = _msgIndex++;
        html += `<div class="msg-feedback">
            <button class="feedback-btn" id="fb-up-${idx}" onclick="submitFeedback(${idx}, 'up')" title="Berguna">👍</button>
            <button class="feedback-btn" id="fb-down-${idx}" onclick="submitFeedback(${idx}, 'down')" title="Tidak berguna">👎</button>
        </div>`;
    }
    msgDiv.innerHTML = html;
    canvasMessages.insertBefore(msgDiv, typingIndicator);
    canvasMessages.scrollTop = canvasMessages.scrollHeight;
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

// Split doc into individual lines — each line is its own matchable unit
function _splitDocLines(text) {
    return text.split('\n').map((line, i) => ({
        line: line,
        trimmed: line.trim(),
        isEmpty: !line.trim(),
        lineIdx: i,
    }));
}

function _matchIssueToLine(issue, allLines) {
    const ne = allLines.filter(l => !l.isEmpty); // non-empty lines
    if (!ne.length) return -1;

    const loc = (issue.location || '').toLowerCase().trim();
    const combined = (loc + ' ' + (issue.issue || '') + ' ' + (issue.suggestion || '')).toLowerCase();

    // 1. Numbered paragraph: "Perenggan 3" → find line starting with "3."
    const numMatch = loc.match(/(?:perenggan|paragraph)\s*(?:ke-?)?(\d+)/);
    if (numMatch) {
        const n = parseInt(numMatch[1]);
        const numbered = ne.find(l => /^\d+[.\s]/.test(l.trimmed) && parseInt(l.trimmed) === n);
        if (numbered) return numbered.lineIdx;
        return ne[n - 1]?.lineIdx ?? -1;
    }

    // 2. Positional heuristics
    if (/(?:pengirim|penghantar|nama.*pengirim|bahagian.*atas|header|ruj\.|no\.\s*ruj)/.test(loc))
        return ne[0].lineIdx;
    if (/(?:penutup|tandatangan|tanda tangan|yang benar|yang menjalankan|sekian|penandatangan)/.test(loc))
        return ne[ne.length - 1].lineIdx;
    if (/(?:tajuk|perkara|subject|heading)/.test(loc)) {
        const caps = ne.find(l => l.trimmed.length > 4 && l.trimmed === l.trimmed.toUpperCase() && !/^[\d\s\.\:\-]+$/.test(l.trimmed));
        if (caps) return caps.lineIdx;
    }
    if (/tarikh|date/.test(loc)) {
        const dl = ne.find(l => /\d{1,2}\s+\w+\s+\d{4}|\d{1,2}[\/\-]\d{1,2}/.test(l.line));
        if (dl) return dl.lineIdx;
    }
    if (/(?:nama penerima|jawatan penerima|alamat penerima|penerima)/.test(loc)) {
        // typically 2nd–4th non-empty line
        return ne[Math.min(2, ne.length - 1)].lineIdx;
    }

    // 3. Keyword search across ALL issue fields
    const stopwords = new Set(['yang','dan','atau','dalam','untuk','pada','dengan','ini','itu','the','and','or','in','for','on','with','di','ke','ia','adalah','telah','akan','tidak','ada','saya','anda','bahawa','kepada','daripada','oleh','juga','sudah']);
    const keywords = combined.split(/[\s,\/\-\(\):;\.\"\']+/).filter(w => w.length > 3 && !stopwords.has(w));
    if (!keywords.length) return -1;

    let bestLineIdx = -1, bestScore = 0;
    ne.forEach(l => {
        const ll = l.line.toLowerCase();
        const score = keywords.reduce((s, kw) => s + (ll.includes(kw) ? 1 : 0), 0);
        if (score > bestScore) { bestScore = score; bestLineIdx = l.lineIdx; }
    });
    return bestScore >= 1 ? bestLineIdx : -1;
}

function toggleRevAnnotation(badge) {
    const popup = badge.nextElementSibling;
    if (!popup || !popup.classList.contains('rev-annotation-popup')) return;
    const isOpen = popup.style.display !== 'none';
    document.querySelectorAll('.rev-annotation-popup').forEach(p => { p.style.display = 'none'; });
    if (!isOpen) {
        const rect = badge.getBoundingClientRect();
        popup.style.display = 'block';
        popup.style.position = 'fixed';
        popup.style.zIndex   = '9999';
        popup.style.right    = 'auto';
        popup.style.bottom   = 'auto';
        const popW = 280, popH = 220;
        // prefer left of badge; fallback to right if too close to edge
        let left = rect.left - popW - 6;
        if (left < 8) left = rect.right + 6;
        if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
        let top = rect.top;
        if (top + popH > window.innerHeight - 8) top = window.innerHeight - popH - 8;
        popup.style.left = Math.max(8, left) + 'px';
        popup.style.top  = Math.max(8, top)  + 'px';
    }
}

function buildReviewHtml(data) {
    const docText = _reviewDocText;

    // If we have the document text, build annotated preview
    if (docText) {
        return _buildAnnotatedReview(data, docText);
    }

    // Fallback: plain list view (no uploaded doc text available)
    let html = '<div class="message-bubble structured-response review-response">';
    if (data.message) html += `<div class="da-message">${escapeHtml(data.message)}</div>`;
    if (data.summary) {
        const scoreColors = { A: '#22c55e', B: '#3b82f6', C: '#f59e0b', D: '#ef4444' };
        const scoreLabels = { A: 'Cemerlang', B: 'Baik', C: 'Perlu Pembetulan', D: 'Banyak Isu' };
        html += `<div class="da-section"><div class="da-section-title">📋 Ringkasan</div>`;
        html += `<p style="font-size:13px;color:var(--text-secondary);line-height:1.6">${escapeHtml(data.summary)}</p>`;
        if (data.score) {
            const color = scoreColors[data.score] || '#888';
            html += `<div class="review-score" style="color:${color};font-weight:bold;margin-top:6px;">Skor: ${data.score} — ${scoreLabels[data.score] || data.score}</div>`;
        }
        html += '</div>';
    }
    if (data.issues && data.issues.length === 0) {
        html += '<div class="da-section"><div class="da-section-title">✅ Tiada Isu</div><p style="font-size:13px;color:var(--text-secondary)">Dokumen ini dalam keadaan baik.</p></div>';
    }
    if (data.corrected_document) {
        html += `<div class="da-section doc-preview-section review-doc-preview-section">`;
        html += `<div class="da-section-title">📄 Dokumen Diperbetulkan <span class="edit-hint">(boleh diedit)</span><button class="doc-preview-expand-btn" onclick="openWordPreview()" title="Besar">&#9974; Lihat Word</button><button class="doc-preview-save-btn" id="docPreviewSaveBtn" onclick="savePreviewEdits(this)">💾 Simpan</button></div>`;
        html += `<pre class="doc-preview" contenteditable="true" id="reviewDocPreview" oninput="onPreviewEdit()">${escapeHtml(data.corrected_document)}</pre>`;
        html += `<div class="doc-actions"><button class="doc-action-btn download-btn" onclick="downloadReviewDocument()">📥 Muat Turun (.docx)</button><button class="doc-action-btn pdf-btn" onclick="downloadDocumentPdf()">📄 Muat Turun (.pdf)</button></div>`;
        html += '</div>';
    }
    html += '</div>';
    return html;
}

// Build the right-side annotation column HTML
function _buildAnnColumn(issues) {
    const wajibCount = issues.filter(i => i.severity === 'WAJIB_BETULKAN').length;
    const cadCount   = issues.length - wajibCount;

    let html = `<div class="rev-ann-column">`;
    html += `<div class="rev-ann-header">`;
    html += `<span class="rev-ann-title">📋 Anotasi</span>`;
    html += `<div class="rev-ann-counts">`;
    if (wajibCount) html += `<span class="rev-count-pill wajib">${wajibCount} Wajib</span>`;
    if (cadCount)   html += `<span class="rev-count-pill cadangan">${cadCount} Cadangan</span>`;
    html += `</div></div>`;

    if (!issues.length) {
        html += '<div class="rev-no-issues" style="padding:12px">✅ Tiada isu ditemui.</div>';
    } else {
        issues.forEach(issue => {
            const bCls = issue.severity === 'WAJIB_BETULKAN' ? 'wajib' : 'cadangan';
            const fixPrompt = escapeAttr(issue.suggestion
                ? `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.suggestion}`
                : `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.issue || ''}`);
            const badgeNav = issue.highlight ? ` onclick="scrollToPdfHighlight(${issue.num})"` : '';
            const badgeCls = issue.highlight ? `${bCls} ann-num clickable` : `${bCls} ann-num`;
            html += `<div class="rev-ann-item" id="annItem_${issue.num}">`;
            html += `<span class="rev-badge ${badgeCls}"${badgeNav} title="${issue.highlight ? 'Pergi ke lokasi dalam PDF' : ''}">${issue.num}</span>`;
            html += `<div class="rev-ann-body">`;
            if (issue.category) html += `<div class="rev-ann-cat">${escapeHtml(issue.category)}</div>`;
            if (issue.location) html += `<div class="rev-ann-loc">📍 ${escapeHtml(issue.location)}</div>`;
            html += `<div class="rev-ann-desc">${escapeHtml(issue.issue || '')}</div>`;
            if (issue.suggestion) html += `<div class="rev-ann-sug">💡 ${escapeHtml(issue.suggestion)}</div>`;
            html += `<button class="ann-fix-btn" data-prompt="${fixPrompt}" onclick="fixReviewIssue(this)">🔧 Betulkan</button>`;
            html += `</div></div>`;
        });
    }
    html += '</div>';
    return html;
}

function _buildAnnotatedReview(data, docText) {
    const issues = data.issues || [];
    const allLines = _splitDocLines(docText);
    const scoreColors = { A: '#22c55e', B: '#3b82f6', C: '#f59e0b', D: '#ef4444' };
    const scoreLabels = { A: 'Cemerlang', B: 'Baik', C: 'Perlu Pembetulan', D: 'Banyak Isu' };
    const scoreColor = scoreColors[data.score] || '#6b7280';

    const isPdfImg = _reviewIsPdf && _reviewPdfImages && _reviewPdfImages.length;

    const lineIssues = {};   // keyed by lineIdx (Word/text preview)
    const pageIssues = {};   // keyed by PDF page index (image preview)
    let orderedIssues;

    if (isPdfImg) {
        // PDF: order issues by highlight position (page, then top-to-bottom)
        const located   = issues.filter(i => i.highlight)
            .sort((a, b) => (a.highlight.page - b.highlight.page) || (a.highlight.y - b.highlight.y));
        const unlocated = issues.filter(i => !i.highlight);
        orderedIssues = [...located, ...unlocated];
        orderedIssues.forEach((issue, i) => { issue.num = i + 1; });
        located.forEach(issue => {
            (pageIssues[issue.highlight.page] = pageIssues[issue.highlight.page] || []).push(issue);
        });
    } else {
        // Word/text: map each issue to its line index in the document
        const issuesMapped = issues.map(issue => ({
            ...issue,
            _lineIdx: _matchIssueToLine(issue, allLines)
        }));
        // Re-number issues in document top-to-bottom order so badge N always
        // matches annotation N in the right column
        const mapped   = issuesMapped.filter(i => i._lineIdx >= 0).sort((a, b) => a._lineIdx - b._lineIdx);
        const unmapped = issuesMapped.filter(i => i._lineIdx < 0);
        [...mapped, ...unmapped].forEach((issue, i) => { issue.num = i + 1; });
        mapped.forEach(issue => {
            if (!lineIssues[issue._lineIdx]) lineIssues[issue._lineIdx] = [];
            lineIssues[issue._lineIdx].push(issue);
        });
        orderedIssues = [...mapped, ...unmapped];
    }

    const docHtml = _reviewDocHtml;
    const isPdf   = _reviewIsPdf;

    // Build DOCX DOM node now (before html string, so real addEventListener works)
    let docxNode = null;
    const docxPlaceholderId = 'revDocxInject_' + Date.now();
    if (!isPdf && docHtml) {
        docxNode = _injectBadgesIntoHtml(docHtml, lineIssues, allLines);
    }

    let html = '<div class="rev-annotated">';

    // ── Score bar ──
    html += '<div class="rev-score-bar">';
    if (data.score) html += `<span class="rev-score-badge" style="background:${scoreColor}">Skor ${data.score} — ${scoreLabels[data.score] || data.score}</span>`;
    if (data.summary) html += `<span class="rev-summary-text">${escapeHtml(data.summary)}</span>`;
    html += '</div>';

    // ── Header: label + action buttons ──
    html += `<div class="rev-doc-header">`;
    html += `<span class="rev-doc-label">📄 Pratonton Dokumen</span>`;
    html += `<div class="rev-header-btns">`;
    html += `<button class="rev-expand-btn" onclick="toggleRevExpand(this)">⛶ Kembangkan</button>`;
    if (isPdf) {
        html += `<button class="rev-download-btn" onclick="downloadUploadedPdf('word')">📥 Word</button>`;
        html += `<button class="rev-download-btn" onclick="downloadUploadedPdf('pdf')">📄 PDF</button>`;
    } else {
        html += `<button class="rev-save-btn" onclick="saveDocEdit(this)" style="display:none">💾 Simpan</button>`;
        html += `<button class="rev-download-btn" onclick="downloadEditedDoc(this)">📥 Muat Turun</button>`;
    }
    html += `</div></div>`;

    // ── Split layout: doc (left) + annotations (right) ──
    html += `<div class="rev-split-layout">`;

    // Left: document preview
    html += `<div class="rev-doc-page">`;
    html += `<button class="rev-close-btn" onclick="toggleRevExpand(this.closest('.rev-annotated').querySelector('.rev-expand-btn'))">✕ Tutup Pratonton</button>`;

    if (isPdf) {
        if (_reviewPdfImages && _reviewPdfImages.length) {
            // Faithful PDF preview: each page as an image with error highlights
            _reviewPdfImages.forEach((src, pi) => {
                html += `<div class="rev-pdf-page-wrap">`;
                html += `<img class="rev-pdf-page" src="${src}" alt="Halaman PDF ${pi + 1}" loading="lazy">`;
                (pageIssues[pi] || []).forEach(iss => {
                    const h = iss.highlight;
                    const cls = iss.severity === 'WAJIB_BETULKAN' ? 'wajib' : 'cadangan';
                    const st = `left:${(h.x * 100).toFixed(2)}%;top:${(h.y * 100).toFixed(2)}%;`
                             + `width:${(h.w * 100).toFixed(2)}%;height:${(h.h * 100).toFixed(2)}%`;
                    html += `<div class="rev-hl ${cls}" id="revHl_${iss.num}" style="${st}" onclick="scrollToAnnotation(${iss.num})" title="Isu ${iss.num}">`
                          + `<span class="rev-hl-num ${cls}">${iss.num}</span></div>`;
                });
                html += `</div>`;
            });
        } else {
            const pdfSrc = _reviewPdfObjectUrl || '';
            html += `<iframe class="rev-pdf-embed" src="${escapeAttr(pdfSrc)}" title="Pratonton PDF"></iframe>`;
        }
    } else if (docxNode) {
        html += `<div class="rev-html-doc" id="${docxPlaceholderId}" contenteditable="true" spellcheck="false" oninput="onDocEdit(this.closest('.rev-annotated'))"></div>`;
    } else {
        // Fallback: plain text rows
        allLines.forEach(lineObj => {
            if (lineObj.isEmpty) { html += '<div class="rev-spacer"></div>'; return; }
            const lIssues = lineIssues[lineObj.lineIdx] || [];
            const hasWajib = lIssues.some(i => i.severity === 'WAJIB_BETULKAN');
            const rowCls = hasWajib ? ' has-wajib' : lIssues.length ? ' has-cadangan' : '';
            html += `<div class="rev-para-row${rowCls}">`;
            html += `<div class="rev-para-text">${escapeHtml(lineObj.line)}</div>`;
            if (lIssues.length) {
                html += '<div class="rev-badges">';
                lIssues.forEach(iss => {
                    const bCls = iss.severity === 'WAJIB_BETULKAN' ? 'wajib' : 'cadangan';
                    html += `<span class="rev-badge ${bCls}" onclick="scrollToAnnotation(${iss.num})">${iss.num}</span>`;
                });
                html += '</div>';
            }
            html += '</div>';
        });
    }

    html += '</div>'; // rev-doc-page

    // Right: annotation column
    html += _buildAnnColumn(orderedIssues);

    html += '</div>'; // rev-split-layout

    // Corrected document section (legacy — from agent corrected_document field)
    if (data.corrected_document) {
        html += `<div class="da-section doc-preview-section review-doc-preview-section">`;
        html += `<div class="da-section-title">📄 Dokumen Diperbetulkan <span class="edit-hint">(boleh diedit)</span><button class="doc-preview-expand-btn" onclick="openWordPreview()" title="Besar">&#9974; Lihat Word</button><button class="doc-preview-save-btn" id="docPreviewSaveBtn" onclick="savePreviewEdits(this)">💾 Simpan</button></div>`;
        html += `<pre class="doc-preview" contenteditable="true" id="reviewDocPreview" oninput="onPreviewEdit()">${escapeHtml(data.corrected_document)}</pre>`;
        html += `<div class="doc-actions"><button class="doc-action-btn download-btn" onclick="downloadReviewDocument()">📥 Muat Turun (.docx)</button><button class="doc-action-btn pdf-btn" onclick="downloadDocumentPdf()">📄 Muat Turun (.pdf)</button></div>`;
        html += '</div>';
    }

    html += '</div>'; // rev-annotated

    // Deferred: inject DOCX DOM node (has real event listeners) into placeholder
    if (docxNode) {
        setTimeout(() => {
            const ph = document.getElementById(docxPlaceholderId);
            if (ph) { while (docxNode.firstChild) ph.appendChild(docxNode.firstChild); }
        }, 0);
    }

    return html;
}

// ── Annotation helpers ──

function scrollToAnnotation(num) {
    const item = document.getElementById(`annItem_${num}`);
    if (!item) return;
    document.querySelectorAll('.rev-ann-item.ann-active').forEach(el => el.classList.remove('ann-active'));
    item.classList.add('ann-active');

    // Scroll the annotation column container (not the whole page)
    const col = item.closest('.rev-ann-column');
    if (col) {
        // getBoundingClientRect gives visual position; add current scrollTop to get
        // the absolute position within the scroll container, then subtract 12px padding
        const targetTop = item.getBoundingClientRect().top
                        - col.getBoundingClientRect().top
                        + col.scrollTop
                        - 12;
        col.scrollTop = targetTop;
    } else {
        item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Reverse of scrollToAnnotation: from an annotation, jump to its highlight on
// the PDF page image and flash it.
function scrollToPdfHighlight(num) {
    const hl = document.getElementById(`revHl_${num}`);
    if (!hl) return;
    const page = hl.closest('.rev-doc-page');
    if (page) {
        const targetTop = hl.getBoundingClientRect().top
                        - page.getBoundingClientRect().top
                        + page.scrollTop - 48;
        page.scrollTo({ top: Math.max(0, targetTop), behavior: 'smooth' });
    } else {
        hl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    // Flash the box to draw the eye
    document.querySelectorAll('.rev-hl.hl-flash').forEach(el => el.classList.remove('hl-flash'));
    void hl.offsetWidth;   // restart animation
    hl.classList.add('hl-flash');
    setTimeout(() => hl.classList.remove('hl-flash'), 1600);
    // Keep the matching annotation marked active
    const item = document.getElementById(`annItem_${num}`);
    if (item) {
        document.querySelectorAll('.rev-ann-item.ann-active').forEach(el => el.classList.remove('ann-active'));
        item.classList.add('ann-active');
    }
}

function highlightDocBadge(num) {
    document.querySelectorAll('.rev-html-doc .rev-badge, .rev-para-row .rev-badge').forEach(b => {
        if (b.textContent.trim() === String(num)) {
            b.classList.add('badge-highlighted');
            b.scrollIntoView({ behavior: 'smooth', block: 'center' });
            setTimeout(() => b.classList.remove('badge-highlighted'), 2200);
        }
    });
}

function onDocEdit(annotated) {
    const saveBtn = annotated?.querySelector('.rev-save-btn');
    if (!saveBtn) return;
    saveBtn.style.display = 'inline-flex';
    saveBtn.classList.add('unsaved');
    saveBtn.textContent = '💾 Simpan*';
}

function saveDocEdit(btn) {
    const annotated = btn.closest('.rev-annotated');
    const htmlDoc = annotated?.querySelector('.rev-html-doc');
    if (htmlDoc) {
        window._savedDocHtml = htmlDoc.innerHTML;
        btn.textContent = '✅ Tersimpan';
        btn.classList.remove('unsaved');
        btn.classList.add('saved');
        setTimeout(() => { btn.textContent = '💾 Simpan'; btn.classList.remove('saved'); }, 2200);
    }
}

// Download the uploaded PDF as the original PDF, or converted to Word (.docx)
async function downloadUploadedPdf(fmt) {
    if (!_reviewPdfObjectUrl) {
        addMessage('Tiada fail PDF untuk dimuat turun.', 'assistant', '⚠️', 'Sistem');
        return;
    }
    const a = document.createElement('a');
    if (fmt === 'pdf') {
        a.href = _reviewPdfObjectUrl;
        a.download = 'dokumen.pdf';
    } else {
        // Word: native browser download from the GET endpoint (uses the
        // server-cached PDF). Direct link click keeps the user-gesture context,
        // so the browser downloads reliably.
        a.href = `/api/review/download-word?session_id=${encodeURIComponent(sessionId)}`;
        a.download = 'dokumen.docx';
    }
    document.body.appendChild(a);
    a.click();
    a.remove();
}

async function downloadEditedDoc(btn) {
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Menyediakan...'; }

    try {
        if (_reviewIsPdf && _reviewPdfObjectUrl) {
            // PDF: download original
            const a = document.createElement('a');
            a.href = _reviewPdfObjectUrl;
            a.download = 'dokumen.pdf';
            a.click();
            return;
        }

        // DOCX: send current edited HTML to server for conversion
        const htmlDoc = document.querySelector('.rev-html-doc');
        const html = (htmlDoc ? htmlDoc.innerHTML : null) || window._savedDocHtml || _reviewDocHtml;
        if (!html) { addMessage('Tiada dokumen untuk dimuat turun.', 'assistant', '⚠️', 'Sistem'); return; }

        const res = await fetch('/api/review/download-edited', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ html, session_id: sessionId })
        });
        if (!res.ok) throw new Error(res.statusText);
        const blob = await res.blob();
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = blob.type.includes('wordprocessingml') ? 'dokumen_disemak.docx' : 'dokumen_disemak.html';
        a.click();
        URL.revokeObjectURL(url);
    } catch (err) {
        addMessage(`Ralat muat turun: ${err.message}`, 'assistant', '⚠️', 'Sistem');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '📥 Muat Turun'; }
    }
}

// Inject numbered badge spans into mammoth HTML using live DOM (no DOMParser serialization issues)
function _injectBadgesIntoHtml(docHtml, lineIssues, allLines) {
    // Use a live DOM element so event handlers survive without serialization
    const tmp = document.createElement('div');
    tmp.style.cssText = 'position:absolute;left:-99999px;top:0;visibility:hidden';
    document.body.appendChild(tmp);
    tmp.innerHTML = docHtml;

    // Build map: lowercased text snippet → issues
    const snippetMap = new Map();
    Object.entries(lineIssues).forEach(([lineIdx, issues]) => {
        const line = allLines[parseInt(lineIdx)];
        if (!line || !line.trimmed || line.trimmed.length < 3) return;
        snippetMap.set(line.trimmed.substring(0, 40).toLowerCase(), issues);
    });

    const candidates = tmp.querySelectorAll('p, td, th, li, h1, h2, h3, h4, h5');
    candidates.forEach(el => {
        const elText = el.textContent.trim().substring(0, 40).toLowerCase();
        if (!elText || elText.length < 3) return;

        let matched = null, usedKey = null;
        for (const [key, issues] of snippetMap) {
            if (elText.includes(key.substring(0, 20)) || key.includes(elText.substring(0, 20))) {
                matched = issues; usedKey = key; break;
            }
        }
        if (!matched) return;
        snippetMap.delete(usedKey);

        const hasWajib = matched.some(i => i.severity === 'WAJIB_BETULKAN');
        el.style.cssText += (hasWajib
            ? ';background:rgba(239,68,68,0.12);border-left:3px solid #ef4444;padding-left:4px'
            : ';background:rgba(245,158,11,0.10);border-left:3px solid #f59e0b;padding-left:4px');
        el.style.position = 'relative';

        const badgeWrap = document.createElement('span');
        badgeWrap.className = 'rev-badges-inline';
        badgeWrap.style.cssText = 'display:inline-flex;align-items:center;gap:3px;margin-left:4px;vertical-align:middle';

        matched.forEach(issue => {
            const bCls = issue.severity === 'WAJIB_BETULKAN' ? 'wajib' : 'cadangan';
            const fixPrompt = issue.suggestion
                ? `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.suggestion}`
                : `Betulkan isu ini dalam dokumen: ${issue.location || ''} — ${issue.issue || ''}`;

            const badge = document.createElement('span');
            badge.className = `rev-badge ${bCls}`;
            badge.textContent = issue.num;
            badge.style.cssText = 'cursor:pointer;vertical-align:middle';
            // Click: scroll to this issue in the right annotation column
            const issueNum = issue.num;
            badge.addEventListener('click', function(e) { e.stopPropagation(); scrollToAnnotation(issueNum); });

            badgeWrap.appendChild(badge);
        });

        el.appendChild(badgeWrap);
    });

    // Return tmp itself — cloneNode would strip event listeners
    document.body.removeChild(tmp);
    return tmp;
}

function toggleRevExpand(btn) {
    if (!btn) return;
    const annotated   = btn.closest('.rev-annotated');
    const splitLayout = annotated?.querySelector('.rev-split-layout');
    const docPage     = annotated?.querySelector('.rev-doc-page');
    if (!splitLayout || !docPage) return;

    const isExpanded = splitLayout.classList.toggle('rev-split-expanded');
    btn.textContent  = isExpanded ? '⛶ Kecilkan' : '⛶ Kembangkan';

    const closeBtn = docPage.querySelector('.rev-close-btn');
    if (closeBtn) closeBtn.style.display = isExpanded ? 'block' : 'none';

    // Prevent body scroll when expanded
    document.body.style.overflow = isExpanded ? 'hidden' : '';
    if (isExpanded) splitLayout.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
    'Penerima':                               { type: 'penerima', ph: 'cth: Semua Pengetua / Rujuk Senarai Edaran / SK Taman Maju' },
    'Nama Organisasi Penerima':               { type: 'text',     ph: 'cth: SMK Taman Maju', hideable: true },
    'Alamat Penerima':                        { type: 'textarea', ph: 'Alamat penuh penerima...', hideable: true },
    'Senarai Edaran':                         { type: 'senarai-edaran', ph: '' },
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
    'Masa Acara':                             { type: 'text',     ph: 'cth: 8.00 pagi' },
    'Nama Organisasi':                        { type: 'text',     ph: 'cth: Pejabat Pendidikan Daerah Dalat' },
    'Nama Pegawai Yang Terlibat':             { type: 'pegawai-list', ph: '' },
    'Jawatan Pegawai Yang Terlibat':          { type: '_skip', ph: '' },
    'Objektif Program':                       { type: 'textarea', ph: 'Nyatakan objektif program...', rows: 3 },
    'Isi Kandungan':                          { type: 'textarea', ph: 'Nyatakan ringkasan atau poin utama (ejen akan jana isi penuh secara automatik)...', rows: 6, expandable: true },
    'Isi Kandungan Utama':                    { type: 'textarea', ph: 'Nyatakan ringkasan atau poin utama (ejen akan jana isi penuh secara automatik)...', rows: 6, expandable: true },
    'Isi Kandungan Utama (pisahkan perenggan dengan baris kosong)': { type: 'textarea', ph: 'Nyatakan ringkasan atau poin utama (ejen akan jana isi penuh secara automatik)...', rows: 6, expandable: true },
    'Rumusan / Laporan Ringkas':              { type: 'textarea', ph: 'Rumusan program (pilihan — boleh dijana automatik)...', rows: 3 },
    'Cadangan / Tindakan Susulan':            { type: 'textarea', ph: 'Cadangan (pilihan — boleh dijana automatik)...', rows: 3 },
    'Nama Penyedia Laporan':                  { type: 'text',     ph: 'cth: Ahmad bin Ali' },
    'Jawatan Penyedia':                       { type: 'text',     ph: 'cth: Penolong PPD' },
    'Nama Pengesah Laporan':                  { type: 'text',     ph: 'cth: Encik Zulkifli bin Hamid' },
    'Jawatan Pengesah':                       { type: 'text',     ph: 'cth: Pegawai Pendidikan Daerah' },
};

const _MS_DAYS   = ['Ahad','Isnin','Selasa','Rabu','Khamis','Jumaat','Sabtu'];
const _MS_MONTHS = ['Januari','Februari','Mac','April','Mei','Jun','Julai','Ogos','September','Oktober','November','Disember'];

function _parseDateInput(val) {
    if (!val) return null;
    // dd/mm/yyyy or dd-mm-yyyy
    let m = val.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
    if (m) return { d: +m[1], mo: +m[2], y: +m[3] };
    // yyyy-mm-dd (ISO from old type=date)
    m = val.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (m) return { d: +m[3], mo: +m[2], y: +m[1] };
    return null;
}

function _formatDateMS(val) {
    if (!val) return '';
    const p = _parseDateInput(val);
    if (!p) return val; // return as-is if unrecognised
    const dt = new Date(p.y, p.mo - 1, p.d);
    return `${p.d} ${_MS_MONTHS[p.mo - 1]} ${p.y} (${_MS_DAYS[dt.getDay()]})`;
}

let _formCounter = 0;

function _buildMissingFieldsForm(missingLabels) {
    if (!missingLabels || missingLabels.length === 0) return '';
    const fid = 'ff_' + (++_formCounter);
    const hasPenerima = missingLabels.includes('Penerima');
    let rows = '';
    missingLabels.forEach(label => {
        const def = _FIELD_DEFS[label] || { type: 'text', ph: '' };
        if (def.type === '_skip') return;
        const iid = `${fid}_${label.replace(/\W/g,'_')}`;

        if (def.type === 'penerima') {
            const seId = `${fid}_se_inline`;
            const widget = `<input class="ff-input" type="text" id="${iid}" data-label="${escapeAttr(label)}" placeholder="${escapeAttr(def.ph)}"
                oninput="_onPenerimaInput(this,'${fid}')">
                <div class="ff-penerima-hint" id="${iid}_hint" style="display:none">
                    <span class="ff-hint-badge">📋 Senarai Edaran dikesan</span> — Sila isi senarai edaran di bawah.
                </div>`;
            rows += `<tr><td><label class="ff-label" for="${iid}">${escapeHtml(label)}</label></td><td>${widget}</td></tr>`;
            rows += `<tr id="${fid}_se_section" style="display:none"><td colspan="2">
                <label class="ff-label">Senarai Edaran</label>
                <div class="ff-se-list" id="${seId}" data-label="Senarai Edaran">
                    <div class="ff-se-header">
                        <span class="ff-se-col ff-se-col-bil">Bil.</span>
                        <span class="ff-se-col ff-se-col-nama">Nama <span class="ff-optional">(boleh kosong)</span></span>
                        <span class="ff-se-col ff-se-col-jawatan">Jawatan</span>
                        <span class="ff-se-col ff-se-col-jabatan">Jabatan / Sekolah</span>
                        <span class="ff-se-col ff-se-col-del"></span>
                    </div>
                    <div class="ff-se-row" data-bil="1">
                        <span class="ff-se-num">1.</span>
                        <input class="ff-input ff-se-nama" type="text" placeholder="Nama (pilihan)">
                        <input class="ff-input ff-se-jawatan" type="text" placeholder="Jawatan">
                        <input class="ff-input ff-se-jabatan" type="text" placeholder="Jabatan / Sekolah">
                        <button type="button" class="ff-ahli-remove" onclick="_removeSERow(this)" title="Buang">✕</button>
                    </div>
                </div>
                <button type="button" class="ff-ahli-add" onclick="_addSERow('${seId}')">+ Tambah Baris</button>
            </td></tr>`;
            return;
        }

        if (def.type === 'senarai-edaran') {
            const widget = `<div class="ff-se-list" id="${iid}" data-label="${escapeAttr(label)}">
                    <div class="ff-se-header">
                        <span class="ff-se-col ff-se-col-bil">Bil.</span>
                        <span class="ff-se-col ff-se-col-nama">Nama <span class="ff-optional">(boleh kosong)</span></span>
                        <span class="ff-se-col ff-se-col-jawatan">Jawatan</span>
                        <span class="ff-se-col ff-se-col-jabatan">Jabatan / Sekolah</span>
                        <span class="ff-se-col ff-se-col-del"></span>
                    </div>
                    <div class="ff-se-row" data-bil="1">
                        <span class="ff-se-num">1.</span>
                        <input class="ff-input ff-se-nama" type="text" placeholder="Nama (pilihan)">
                        <input class="ff-input ff-se-jawatan" type="text" placeholder="Jawatan" required>
                        <input class="ff-input ff-se-jabatan" type="text" placeholder="Jabatan / Sekolah" required>
                        <button type="button" class="ff-ahli-remove" onclick="_removeSERow(this)" title="Buang">✕</button>
                    </div>
                </div>
                <div class="ff-ahli-actions">
                    <button type="button" class="ff-ahli-add" onclick="_addSERow('${iid}')">＋ Tambah Penerima</button>
                </div>`;
            rows += `<tr class="ff-span"><td colspan="2"><label class="ff-label">${escapeHtml(label)}</label>${widget}</td></tr>`;
            return;
        }

        const isWide = def.type === 'textarea' || def.type === 'ahli-list' || def.type === 'pegawai-list';
        if (isWide) {
            let widget = '';
            if (def.type === 'textarea') {
                const taClass = def.expandable ? 'ff-input ff-expandable' : 'ff-input';
                const taOnInput = def.expandable ? ' oninput="this.style.height=\'auto\';this.style.height=this.scrollHeight+\'px\'"' : '';
                widget = `<textarea class="${taClass}" id="${iid}" data-label="${escapeAttr(label)}" placeholder="${escapeAttr(def.ph)}" rows="${def.rows || 2}"${taOnInput}></textarea>`;
            } else {
                const addLabel = def.type === 'pegawai-list' ? '＋ Tambah Pegawai' : '＋ Tambah Ahli';
                const namaPh  = def.type === 'pegawai-list' ? 'Nama pegawai' : 'Nama ahli';
                const extraAttr = def.type === 'pegawai-list' ? ' data-type="pegawai-list"' : '';
                const semuaBtn = def.type === 'pegawai-list'
                    ? `<button type="button" class="ff-ahli-semua" onclick="_toggleSemuaHadir('${iid}')">☑ Semua Guru/Staf Hadir</button>`
                    : '';
                widget = `<div class="ff-ahli-list" id="${iid}" data-label="${escapeAttr(label)}"${extraAttr}>
                    <div class="ff-ahli-row">
                        <input class="ff-input ff-ahli-nama" type="text" placeholder="${namaPh}">
                        <input class="ff-input ff-ahli-jawatan" type="text" placeholder="Jawatan">
                        <button type="button" class="ff-ahli-remove" onclick="_removeAhliRow(this)" title="Buang">✕</button>
                    </div>
                </div>
                <div class="ff-ahli-actions">
                    <button type="button" class="ff-ahli-add" onclick="_addAhliRow('${iid}')">${addLabel}</button>
                    ${semuaBtn}
                </div>`;
            }
            const shouldHide = def.hideable && hasPenerima;
            const hideAttr = shouldHide ? ` id="${fid}_hide_${iid}" style="display:none"` : '';
            rows += `<tr class="ff-span"${hideAttr}><td colspan="2"><label class="ff-label" for="${iid}">${escapeHtml(label)}</label>${widget}</td></tr>`;
        } else {
            let input = '';
            if (def.type === 'date') {
                input = `<input class="ff-input ff-date" type="text" id="${iid}" data-label="${escapeAttr(label)}" data-is-date="1" placeholder="cth: 22/07/2026" oninput="_onDateChange(this,'${fid}')">`;
            } else {
                input = `<input class="ff-input" type="text" id="${iid}" data-label="${escapeAttr(label)}" placeholder="${escapeAttr(def.ph)}">`;
            }
            const shouldHide = def.hideable && hasPenerima;
            const hideAttr = shouldHide ? ` id="${fid}_hide_${iid}" style="display:none"` : '';
            rows += `<tr${hideAttr}><td><label class="ff-label" for="${iid}">${escapeHtml(label)}</label></td><td>${input}</td></tr>`;
        }
    });
    return `<div class="da-section fields-form-section">
        <div class="da-section-title">\u{1F4DD} Sila Isikan Maklumat</div>
        <form class="fields-form" id="${fid}" onsubmit="event.preventDefault();_submitFieldsForm('${fid}')">
        <table class="ff-table"><tbody>${rows}</tbody></table>
        <table class="ff-table"><tbody><tr class="ff-submit-row"><td colspan="2">
            <button type="submit" class="ff-submit-btn">\u{1F4E4} Hantar Maklumat</button>
        </td></tr></tbody></table>
        </form></div>`;
}

function _onPenerimaInput(input, fid) {
    const hint = document.getElementById(input.id + '_hint');
    const seSection = document.getElementById(fid + '_se_section');
    const val = input.value.trim();
    const isSE = /senarai\s*edaran/i.test(val);
    // Generic patterns: "Rujuk...", "Semua...", "SK ...", "SMK ...", empty
    const isGeneric = !val || isSE || /^(semua|rujuk|sk\b|smk\b)/i.test(val);
    if (hint) hint.style.display = isSE ? 'block' : 'none';
    if (seSection) seSection.style.display = isSE ? '' : 'none';
    // Show/hide hideable fields (Nama Organisasi, Alamat) — only visible for specific names
    const form = document.getElementById(fid);
    if (form) {
        form.querySelectorAll('[id*="_hide_"]').forEach(row => {
            row.style.display = isGeneric ? 'none' : '';
        });
    }
}

function _addSERow(listId) {
    const list = document.getElementById(listId);
    if (!list) return;
    const rows = list.querySelectorAll('.ff-se-row');
    const bil = rows.length + 1;
    const div = document.createElement('div');
    div.className = 'ff-se-row';
    div.dataset.bil = bil;
    div.innerHTML = `<span class="ff-se-num">${bil}.</span>
        <input class="ff-input ff-se-nama" type="text" placeholder="Nama (pilihan)">
        <input class="ff-input ff-se-jawatan" type="text" placeholder="Jawatan">
        <input class="ff-input ff-se-jabatan" type="text" placeholder="Jabatan / Sekolah">
        <button type="button" class="ff-ahli-remove" onclick="_removeSERow(this)" title="Buang">✕</button>`;
    list.appendChild(div);
    _renumberSERows(list);
}

function _removeSERow(btn) {
    const list = btn.closest('.ff-se-list');
    if (!list) return;
    if (list.querySelectorAll('.ff-se-row').length <= 1) return;
    btn.closest('.ff-se-row').remove();
    _renumberSERows(list);
}

function _renumberSERows(list) {
    list.querySelectorAll('.ff-se-row').forEach((row, i) => {
        const num = row.querySelector('.ff-se-num');
        if (num) num.textContent = (i + 1) + '.';
    });
}

function _onDateChange(input, fid) {
    if (!input.value) return;
    const p = _parseDateInput(input.value);
    if (!p) return;
    const day = _MS_DAYS[new Date(p.y, p.mo - 1, p.d).getDay()];
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

function _toggleSemuaHadir(listId) {
    const list = document.getElementById(listId);
    if (!list) return;
    const btn = list.parentElement.querySelector('.ff-ahli-semua');
    const isActive = btn && btn.classList.contains('active');

    if (isActive) {
        // Deactivate — clear and restore one blank row
        btn.classList.remove('active');
        btn.textContent = '☑ Semua Guru/Staf Hadir';
        list.innerHTML = `<div class="ff-ahli-row">
            <input class="ff-input ff-ahli-nama" type="text" placeholder="Nama pegawai">
            <input class="ff-input ff-ahli-jawatan" type="text" placeholder="Jawatan">
            <button type="button" class="ff-ahli-remove" onclick="_removeAhliRow(this)" title="Buang">✕</button>
        </div>`;
        list.parentElement.querySelector('.ff-ahli-add').style.display = '';
    } else {
        // Activate — ask for count then fill single row
        const bilangan = prompt('Berapa ramai guru/staf yang hadir?\n(Tekan OK untuk teruskan atau biarkan kosong)', '');
        if (bilangan === null) return; // cancelled
        const namaEntry = bilangan.trim()
            ? `Semua Guru dan Staf Yang Hadir (${bilangan.trim()} orang)`
            : 'Semua Guru dan Staf Yang Hadir';
        if (btn) {
            btn.classList.add('active');
            btn.textContent = '✕ Batal Semua Hadir';
        }
        list.innerHTML = `<div class="ff-ahli-row ff-ahli-row-semua">
            <input class="ff-input ff-ahli-nama" type="text" value="${escapeAttr(namaEntry)}" readonly>
            <input class="ff-input ff-ahli-jawatan" type="text" placeholder="Jawatan (cth: Guru)" value="Guru dan Staf">
            <button type="button" class="ff-ahli-remove" onclick="_removeAhliRow(this)" title="Buang">✕</button>
        </div>`;
        list.parentElement.querySelector('.ff-ahli-add').style.display = 'none';
    }
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
        // Skip fields inside hidden rows
        const parentRow = el.closest('tr[id*="_hide_"], tr[style*="display: none"], tr[style*="display:none"]');
        if (parentRow && parentRow.style.display === 'none') return;
        if (el.classList.contains('ff-se-list')) {
            // Senarai Edaran — serialize as JSON
            const entries = [];
            el.querySelectorAll('.ff-se-row').forEach(row => {
                const nama    = row.querySelector('.ff-se-nama')?.value.trim() || '';
                const jawatan = row.querySelector('.ff-se-jawatan')?.value.trim() || '';
                const jabatan = row.querySelector('.ff-se-jabatan')?.value.trim() || '';
                if (jawatan || jabatan) entries.push({ nama, jawatan, jabatan });
            });
            if (entries.length) parts.push(`${el.dataset.label}: ${JSON.stringify(entries)}`);
        } else if (el.classList.contains('ff-ahli-list')) {
            const isPegawai = el.dataset.type === 'pegawai-list';
            const names = [], jawatans = [];
            el.querySelectorAll('.ff-ahli-row').forEach(row => {
                const nama = row.querySelector('.ff-ahli-nama').value.trim();
                const jawatan = row.querySelector('.ff-ahli-jawatan').value.trim();
                if (nama) { names.push(nama); jawatans.push(jawatan || nama); }
            });
            if (isPegawai) {
                if (names.length) {
                    parts.push(`${el.dataset.label}: ${names.join(', ')}`);
                    parts.push(`Jawatan Pegawai Yang Terlibat: ${jawatans.join(', ')}`);
                }
            } else {
                const entries = names.map((n, i) => jawatans[i] ? `${n} (${jawatans[i]})` : n);
                if (entries.length) parts.push(`${el.dataset.label}: ${entries.join(', ')}`);
            }
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
    const missingLabels = data.fields_status?.missing || [];
    const extraLabels = data.fields_status?.form_extras || [];
    const allFormLabels = [...missingLabels, ...extraLabels];
    const hasMissingFields = allFormLabels.length > 0;
    let html = `<div class="message-bubble structured-response${hasMissingFields ? ' has-form' : ''}">`;

    if (!hasMissingFields) {
        // Guard: never show raw JSON in the message area
        const _rawMsg = data.message || '';
        const _safeMsg = _rawMsg.trim().startsWith('{') ? '' : _rawMsg;
        if (_safeMsg) html += `<div class="da-message">${escapeHtml(_safeMsg)}</div>`;
    }

    // Maklumat terkumpul disembunyikan — bekerja di belakang tabir

    if (hasMissingFields) {
        html += _buildMissingFieldsForm(allFormLabels);
    }

    if (data.document_preview) {
        html += '<div class="da-section doc-preview-section">';
        html += '<div class="da-section-title">📄 Pratonton Dokumen <span class="edit-hint">(boleh diedit)</span>'
            + `<button class="doc-preview-expand-btn" onclick="openWordPreview()" title="Besar">&#9974; Lihat Word</button>`
            + `<button class="doc-preview-save-btn" id="docPreviewSaveBtn" onclick="savePreviewEdits(this)">💾 Simpan</button></div>`;
        if (data.document_html) {
            html += `<pre class="doc-preview" contenteditable="true" id="docPreview" style="display:none" oninput="onPreviewEdit()">${escapeHtml(data.document_preview)}</pre>`;
            html += `<div class="doc-preview doc-preview-html" contenteditable="true" id="docPreviewHtml" oninput="onPreviewEdit()">${data.document_html}</div>`;
        } else {
            html += `<pre class="doc-preview" contenteditable="true" id="docPreview" oninput="onPreviewEdit()">${escapeHtml(data.document_preview)}</pre>`;
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
        html += `<button class="doc-action-btn download-btn" onclick="downloadDocument()">📥 Muat Turun (.docx)</button>`;
        html += `<button class="doc-action-btn pdf-btn" onclick="downloadDocumentPdf()">📄 Muat Turun (.pdf)</button>`;
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
let _activeLetterMsgDiv = null;
let _activeWorkItem = null;
let _activeChatBubble = null;

function fixReviewIssue(btn) {
    const prompt = btn.dataset.prompt;
    if (!prompt) return;
    btn.textContent = '⏳ Sedang diproses...';
    btn.disabled = true;
    btn.classList.add('fix-processing');
    _pendingFixBtn = btn;
    _pendingFixMsgDiv = btn.closest('.work-item') || btn.closest('.message');
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
    _pendingLetterMsgDiv = btn.closest('.work-item') || btn.closest('.message');
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
    const btn = document.querySelector('.doc-action-btn.download-btn');
    const origText = btn ? btn.innerHTML : null;
    if (btn) { btn.disabled = true; btn.innerHTML = '⏳ Menyediakan...'; }
    const previewHtml = document.getElementById('docPreviewHtml');
    if (previewHtml) await saveDocumentEdits(previewHtml.innerText);
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
    finally { if (btn) { btn.disabled = false; btn.innerHTML = origText; } }
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

// Show save button in inline pratonton when user edits
function onPreviewEdit() {
    const btn = document.getElementById('docPreviewSaveBtn');
    if (!btn) return;
    btn.style.display = 'inline-flex';
    btn.classList.add('unsaved');
    btn.textContent = '💾 Simpan*';
}

// Save inline pratonton edits
async function savePreviewEdits(btn) {
    const previewHtml = document.getElementById('docPreviewHtml');
    const preview = document.getElementById('docPreview') || document.getElementById('reviewDocPreview');
    const content = previewHtml ? previewHtml.innerText : (preview ? preview.innerText : '');
    await saveDocumentEdits(content);
    if (btn) {
        btn.textContent = '✅ Tersimpan';
        btn.classList.remove('unsaved');
        btn.classList.add('saved');
        setTimeout(() => {
            btn.textContent = '💾 Simpan';
            btn.style.display = 'none';
            btn.classList.remove('saved');
        }, 2200);
    }
}

// Sync overlay edits back to inline preview and show save button
function onOverlayEdit() {
    const editEl = document.getElementById('wordPreviewHtmlEdit');
    const inlineHtml = document.getElementById('docPreviewHtml');
    if (editEl && inlineHtml) inlineHtml.innerHTML = editEl.innerHTML;

    const saveBtn = document.getElementById('overlaySaveBtn');
    if (saveBtn) {
        saveBtn.classList.add('unsaved');
        saveBtn.textContent = '💾 Simpan*';
    }
}

// Save overlay edits
async function saveOverlayEdits(btn) {
    const editEl = document.getElementById('wordPreviewHtmlEdit');
    const previewText = document.getElementById('wordPreviewText');
    const content = editEl ? editEl.innerText : (previewText ? previewText.innerText : '');
    await saveDocumentEdits(content);
    if (btn) {
        btn.textContent = '✅ Tersimpan';
        btn.classList.remove('unsaved');
        btn.classList.add('saved');
        setTimeout(() => {
            btn.textContent = '💾 Simpan';
            btn.classList.remove('saved', 'unsaved');
        }, 2200);
    }
    // Also update inline save button state
    const inlineSaveBtn = document.getElementById('docPreviewSaveBtn');
    if (inlineSaveBtn) { inlineSaveBtn.style.display = 'none'; inlineSaveBtn.classList.remove('unsaved', 'saved'); }
}

// Download current document as PDF — direct download, no print dialog
async function downloadDocumentPdf() {
    const btn = document.querySelector('.doc-action-btn.pdf-btn');
    const origText = btn ? btn.innerHTML : null;
    if (btn) { btn.disabled = true; btn.innerHTML = '⏳ Menyediakan...'; }
    const previewHtml = document.getElementById('docPreviewHtml') || document.getElementById('wordPreviewHtmlEdit');
    const preview     = document.getElementById('docPreview') || document.getElementById('reviewDocPreview') || document.getElementById('wordPreviewText');
    const html = previewHtml ? previewHtml.innerHTML : (preview ? `<pre style="font-family:Arial,sans-serif;font-size:12pt;white-space:pre-wrap">${preview.innerText}</pre>` : '');
    if (!html) { if (btn) { btn.disabled = false; btn.innerHTML = origText; } return; }

    // Determine filename from agent and document type
    let filename;
    if (currentAgent === 'letter_generator') {
        // Distinguish memo from surat rasmi by content
        filename = html.includes('MEMO DALAMAN') ? 'memo' : 'surat_rasmi';
    } else {
        const agentNames = { report_generator: 'laporan', data_analysis: 'analisis', document_reviewer: 'semakan' };
        filename = agentNames[currentAgent] || 'dokumen';
    }
    filename += '.pdf';

    try {
        const res = await fetch('/api/export/pdf', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ html, filename })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            alert(err.error || 'Gagal hasilkan PDF. Sila cuba semula.');
            return;
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
    } catch (e) {
        alert('Ralat muat turun PDF: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = origText; }
    }
}

function showEmailDialog() {
    const previewHtml = document.getElementById('docPreviewHtml');
    if (previewHtml) saveDocumentEdits(previewHtml.innerText);

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
    } else if (currentAgent === 'letter_generator') {
        await lgHandleLetterPdfUpload(file);
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
            _reviewDocText = data.text || null;
            _reviewDocHtml = data.html || null;
            _reviewIsPdf   = data.is_pdf || false;
            _reviewPdfImages = data.pdf_images || [];
            // For PDF: create a blob URL from the original file (used for download)
            if (_reviewIsPdf) {
                if (_reviewPdfObjectUrl) URL.revokeObjectURL(_reviewPdfObjectUrl);
                _reviewPdfObjectUrl = URL.createObjectURL(file);
            } else {
                if (_reviewPdfObjectUrl) URL.revokeObjectURL(_reviewPdfObjectUrl);
                _reviewPdfObjectUrl = null;
            }
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
        // Prefer the backend's parsed object; fall back to parsing the response
        let structured = result.structured || null;
        if (!structured) { try { structured = JSON.parse(result.response); } catch (_) {} }
        // Never dump raw JSON into the chat if parsing failed
        let chatContent = result.response;
        if (!structured && typeof chatContent === 'string' && chatContent.trim().startsWith('{')) {
            chatContent = 'Maaf, semakan menghasilkan output yang tidak lengkap. Sila cuba semak semula dokumen.';
        }
        addMessage(chatContent, 'assistant', info.icon, info.name, structured);
    } catch (err) {
        typingIndicator.classList.remove('active');
        addMessage(`Ralat: ${err.message}`, 'assistant', '⚠️', 'Sistem');
    } finally { setProcessing(false); }
}

async function lgHandleLetterPdfUpload(file) {
    // Had saiz 10MB — semak di frontend sebelum hantar
    if (file.size > 10 * 1024 * 1024) {
        addMessage('Fail terlalu besar (melebihi 10MB). Sila gunakan PDF yang lebih kecil.', 'assistant', '⚠️', 'Sistem');
        return;
    }
    setProcessing(true);
    addMessage(`📎 Menganalisis PDF: ${file.name}...`, 'user');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    try {
        const res = await fetch('/api/letter/upload-pdf', { method: 'POST', body: formData });
        const data = await res.json();
        if (data.ok) {
            uploadBtn.classList.add('has-file');
            fileIndicator.style.display = 'flex';
            const pagesNote = data.pages_note || '';
            fileIndicatorText.textContent = `📄 ${data.filename} (${data.char_count} aksara diekstrak${pagesNote})`;
            canvasWelcome.style.display = 'none';
            // Papar ringkasan PDF dalam chat sebelum trigger AI form
            const fields = data.extracted_fields || {};
            const fieldLines = Object.entries(fields).map(([k, v]) => `• ${k}: ${v}`).join('\n');
            const docTypeLabel = data.suggested_type === 'memo' ? 'Memo Dalaman' : 'Surat Rasmi';
            const summaryMsg = `📄 PDF berjaya dianalisis.\n\n`
                + (data.analysis_summary ? `${data.analysis_summary}\n\n` : '')
                + `Jenis dokumen dicadangkan: ${docTypeLabel}\n`
                + (fieldLines ? `\nMaklumat yang diekstrak:\n${fieldLines}\n` : '\nTiada maklumat khusus dapat diekstrak. Sila isi borang secara manual.\n')
                + `\nSila lengkapkan borang di bawah untuk jana surat.`;
            addMessage(summaryMsg, 'assistant', '📄', 'Penjana Surat Rasmi');
            await lgSendPdfAnalysisRequest(file.name, data.analysis_summary, data.suggested_type, data.extracted_fields);
        } else {
            addMessage(data.error || 'Gagal memproses PDF.', 'assistant', '⚠️', 'Sistem');
        }
    } catch (err) {
        addMessage(`Ralat muat naik: ${err.message}`, 'assistant', '⚠️', 'Sistem');
    } finally { setProcessing(false); }
}

async function lgSendPdfAnalysisRequest(filename, summary, suggestedType, extractedFields) {
    const fieldsInfo = extractedFields && Object.keys(extractedFields).length > 0
        ? ` Maklumat berikut telah diekstrak: ${Object.entries(extractedFields).map(([k,v]) => `${k}: ${v}`).join(', ')}.`
        : '';
    const msg = currentLang === 'bm'
        ? `Saya telah memuat naik PDF "${filename}".${fieldsInfo} ${summary || ''} Sila jana surat pemakluman berdasarkan dokumen PDF ini dan mulakan proses pengisian borang. Saya perlukan surat pemakluman yang memaklumkan penerima tentang kandungan dokumen asal tersebut.`
        : `I uploaded PDF "${filename}".${fieldsInfo} ${summary || ''} Please generate a notification/forwarding letter (surat pemakluman) based on this PDF document and begin the form filling process.`;

    setProcessing(true);
    typingIndicator.classList.add('active');
    canvasMessages.scrollTop = canvasMessages.scrollHeight;
    try {
        const res = await fetch('/api/agent-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, session_id: sessionId, agent: 'letter_generator', lang: currentLang }),
        });
        const result = await res.json();
        typingIndicator.classList.remove('active');
        const info = getAgentInfo('letter_generator');
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

const _FOLLOWUP_NO_RE  = /^(tidak|tak|no\b|nope|tidak perlu|tiada|sudah cukup|dah cukup|ok terima kasih|ok thanks|tidak ada|tiada lagi|itu sahaja|that'?s? all|selesai|habis|bye|selamat tinggal|tq\b|terima kasih sahaja)/i;
const _FOLLOWUP_YES_RE = /^(ya\b|yes\b|ada\b|ada lagi|boleh|okay|ok\b|nak\b|mahu\b|ingin\b|please\b|tolong\b|saya nak|saya mahu|saya ada)/i;

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message || isProcessing) return;
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // ── Followup handling: ya/tidak selepas dokumen siap ──
    if (_awaitingFollowup) {
        _awaitingFollowup = false;
        if (!_suppressUserMsg) addMessage(message, 'user');
        _suppressUserMsg = false;

        if (_FOLLOWUP_NO_RE.test(message.trim())) {
            await sendFarewell();
            setProcessing(false);
            return;
        }
        if (_FOLLOWUP_YES_RE.test(message.trim())) {
            const info = getAgentInfo(currentAgent);
            const yesMsg = currentLang === 'en'
                ? 'Sure! Please tell me what you need and I will help you right away.'
                : 'Baik! Sila beritahu apa yang perlu dan saya akan bantu dengan segera.';
            addMessage(yesMsg, 'assistant', info.icon, info.name);
            setProcessing(false);
            return;
        }
        // Jawapan lain — hantar ke AI seperti biasa (fall through)
    }

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

        // Tanya followup jika dokumen baru sahaja siap
        if (data.structured?.ready_to_save && !_awaitingFollowup) {
            _awaitingFollowup = true;
            const info = getAgentInfo(currentAgent || lastActiveAgent);
            const followupMsg = currentLang === 'en'
                ? 'Is there anything else I can help you with?'
                : 'Adakah terdapat perkara lain yang boleh saya bantu?';
            setTimeout(() => addMessage(followupMsg, 'assistant', info.icon, info.name), 600);
        }
    } catch (err) {
        addMessage(`${currentLang === 'en' ? 'Error' : 'Ralat'}: ${err.message}. ${I18N[currentLang].error_conn}`, 'assistant', '⚠️', currentLang === 'en' ? 'System' : 'Sistem');
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

// ═══ Resize handle drag ═══
(function() {
    const handle = document.getElementById('resizeHandle');
    const chatPanel = document.getElementById('chatPanel');
    if (!handle || !chatPanel) return;
    let dragging = false, startX = 0, startW = 0;
    handle.addEventListener('mousedown', e => {
        dragging = true; startX = e.clientX; startW = chatPanel.offsetWidth;
        handle.classList.add('resizing');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });
    document.addEventListener('mousemove', e => {
        if (!dragging) return;
        const newW = Math.min(Math.max(startW + (e.clientX - startX), 240), window.innerWidth * 0.6);
        chatPanel.style.width = newW + 'px';
    });
    document.addEventListener('mouseup', () => {
        if (!dragging) return;
        dragging = false;
        handle.classList.remove('resizing');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    });
})();
document.getElementById('canvasHistoryBtn').addEventListener('click', toggleHistory);
document.getElementById('historyBtn').addEventListener('click', toggleHistory);
document.getElementById('historyCloseBtn').addEventListener('click', toggleHistory);
historyOverlay.addEventListener('click', toggleHistory);
document.getElementById('langToggle').addEventListener('click', toggleLanguage);
applyLanguage(currentLang);

// Agent cards
document.querySelectorAll('.agent-card').forEach(card => {
    card.addEventListener('click', () => {
        if (card.dataset.agent === 'kpm_support') openKpmBubble();
        else openAgent(card.dataset.agent);
    });
});

// ═══════════════════════════════════════
//  KPM SUPPORT CHAT BUBBLE
// ═══════════════════════════════════════
let _kpmSessionId = null;
let _kpmReady = false;

function openKpmBubble() {
    const overlay = document.getElementById('kpmChatBubble');
    const avatar = document.getElementById('kpmAvatar');
    if (!overlay) return;
    overlay.style.display = 'flex';
    requestAnimationFrame(() => {
        overlay.classList.add('active', 'open');
        if (avatar) {
            avatar.classList.remove('av-out');
            void avatar.offsetWidth; // reflow
            avatar.classList.add('av-in');
        }
    });
    document.getElementById('kpmBubbleInput').focus();
    if (!_kpmReady) {
        _kpmSessionId = 'sess_kpm_' + Date.now();
        _kpmReady = true;
        _sendKpmIntro();
    }
}

function closeKpmBubbleWithFarewell() {
    if (!_kpmReady) { closeKpmBubble(); return; }
    const farewell = currentLang === 'en'
        ? `Thank you for using SMARTAssist Hub KPM Support. Have a great day! 😊`
        : `Terima kasih kerana menggunakan khidmat SMARTAssist Hub Sokongan KPM. Semoga hari tuan/puan menyenangkan! 😊`;
    _appendKpmMsg(farewell, 'bot');
    setTimeout(() => closeKpmBubble(), 2000);
}

function closeKpmBubble() {
    const overlay = document.getElementById('kpmChatBubble');
    const avatar = document.getElementById('kpmAvatar');
    if (!overlay) return;
    if (avatar) {
        avatar.classList.remove('av-in');
        void avatar.offsetWidth;
        avatar.classList.add('av-out');
    }
    overlay.classList.remove('open');
    setTimeout(() => {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
        if (avatar) avatar.classList.remove('av-out');
        // Reset session so next open starts fresh
        _kpmSessionId = null;
        _kpmReady = false;
        const msgs = document.getElementById('kpmBubbleMessages');
        if (msgs) msgs.innerHTML = '';
    }, 420);
}

function _appendKpmMsg(text, role) {
    const msgs = document.getElementById('kpmBubbleMessages');
    if (!msgs) return;
    const div = document.createElement('div');
    div.className = 'kpm-bubble-msg ' + role;
    // Convert newlines to <br> and escape HTML
    div.innerHTML = escapeHtml(text).replace(/\n/g, '<br>');
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

async function _sendKpmIntro() {
    const typing = document.getElementById('kpmBubbleTyping');
    typing.style.display = 'flex';
    try {
        const res = await fetch('/api/agent-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: '__INTRO__', agent: 'kpm_support', session_id: _kpmSessionId, lang: currentLang }),
        });
        const data = await res.json();
        typing.style.display = 'none';
        _appendKpmMsg(data.response || '', 'bot');
    } catch {
        typing.style.display = 'none';
        _appendKpmMsg(currentLang === 'en' ? 'Hello! I am KPM Support. How can I help you?' : 'Salam! Saya Sokongan KPM. Apa yang boleh saya bantu?', 'bot');
    }
}

const _KPM_FAREWELL_RE = /\b(terima\s*kasih|thank\s*you|thanks|bye|goodbye|selamat\s*tinggal|jumpa\s*lagi|tq\b|ok\s*terima|sudah\s*selesai|dah\s*selesai|habis\s*dah|itu\s*sahaja|that'?s?\s*all)\b/i;

async function sendKpmBubbleMsg() {
    const input = document.getElementById('kpmBubbleInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    _appendKpmMsg(text, 'user');

    // Farewell detection — reply locally then auto-close
    if (_KPM_FAREWELL_RE.test(text)) {
        const farewell = currentLang === 'en'
            ? `Thank you for using SMARTAssist Hub KPM Support. Have a great day! 😊`
            : `Terima kasih kerana menggunakan khidmat SMARTAssist Hub Sokongan KPM. Semoga hari tuan/puan menyenangkan! 😊`;
        setTimeout(() => {
            _appendKpmMsg(farewell, 'bot');
            setTimeout(() => closeKpmBubble(), 2000);
        }, 600);
        return;
    }

    const typing = document.getElementById('kpmBubbleTyping');
    typing.style.display = 'flex';
    document.getElementById('kpmBubbleMessages').scrollTop = 99999;
    try {
        const res = await fetch('/api/agent-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, agent: 'kpm_support', session_id: _kpmSessionId, lang: currentLang }),
        });
        const data = await res.json();
        typing.style.display = 'none';
        _appendKpmMsg(data.response || '', 'bot');
    } catch {
        typing.style.display = 'none';
        _appendKpmMsg(I18N[currentLang].error_generic, 'bot');
    }
}

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
    // Fall back to reviewer corrected-document preview if main preview not present
    const preview = document.getElementById('docPreview') || document.getElementById('reviewDocPreview');
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
    const _htmlContent = isHtmlMode ? previewHtml.innerHTML : null;
    if (isHtmlMode) {
        // Render single hidden page first to measure true content height
        pagesHtml = `<div id="_wordHtmlMeasure" class="word-page" style="position:fixed;top:-9999px;left:-9999px;visibility:hidden;pointer-events:none;max-height:none;overflow:visible"><div class="word-page-html-content">${_htmlContent}</div></div>`;
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
                <button class="word-preview-save-btn" id="overlaySaveBtn" onclick="saveOverlayEdits(this)">💾 Simpan</button>
                <button class="word-preview-pdf-btn" onclick="downloadDocumentPdf()">📄 PDF</button>
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

    // HTML mode: measure rendered height then paginate if content exceeds one A4 page
    if (isHtmlMode) {
        requestAnimationFrame(() => {
            const measure = document.getElementById('_wordHtmlMeasure');
            if (!measure) return;
            const contentEl = measure.querySelector('.word-page-html-content');
            const totalH = contentEl ? contentEl.scrollHeight : measure.scrollHeight;
            measure.remove();

            const MM_TO_PX = 3.7795;
            // A4 content area height: 297mm - 25.4mm top - 25.4mm bottom = 246.2mm
            const pageContentH = Math.round(246.2 * MM_TO_PX);
            // Single-page threshold: full page height minus top padding only (96px).
            // Allows content that fits within the printable area to stay on 1 page
            // even if it slightly exceeds pageContentH due to letterhead or tight spacing.
            const singlePageH = Math.round(297 * MM_TO_PX) - 96;
            const numPages = totalH <= singlePageH ? 1 : Math.max(2, Math.ceil(totalH / pageContentH));
            const scroll = document.querySelector('#wordPreviewOverlay .word-preview-scroll');
            if (!scroll) return;

            if (numPages <= 1) {
                scroll.innerHTML = `<div class="word-page"><div class="word-page-html-content" contenteditable="true" id="wordPreviewHtmlEdit" spellcheck="false" oninput="onOverlayEdit()">${_htmlContent}</div></div>`;
            } else {
                // Multi-page: page 1 is editable; pages 2+ are read-only overflow views
                scroll.innerHTML = Array.from({ length: numPages }, (_, i) => {
                    const offsetPx = i * pageContentH;
                    const pageNum = `<div class="word-page-num">${i + 1} / ${numPages}</div>`;
                    const editAttrs = i === 0 ? `contenteditable="true" id="wordPreviewHtmlEdit" spellcheck="false" oninput="onOverlayEdit()"` : '';
                    // Clip wrapper ensures content is cut at exactly pageContentH — no overlap between pages
                    return `<div class="word-page" style="overflow:hidden;max-height:297mm;min-height:297mm">
                        <div style="overflow:hidden;height:${pageContentH}px">
                            <div class="word-page-html-content" ${editAttrs} style="position:relative;top:-${offsetPx}px">${_htmlContent}</div>
                        </div>
                        ${pageNum}
                    </div>`;
                }).join('');
            }
        });
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
    closeProfilePanel();
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

// ═══════════════════════════════════════
//  PROFILE PANEL
// ═══════════════════════════════════════

const profilePanel   = document.getElementById('profilePanel');
const profileOverlay = document.getElementById('profileOverlay');
const profileBtn     = document.getElementById('profileBtn');
const profileCloseBtn = document.getElementById('profileCloseBtn');

function openProfilePanel() {
    profilePanel.classList.add('open');
    profileOverlay.classList.add('open');
    loadProfile();
}

function closeProfilePanel() {
    profilePanel.classList.remove('open');
    profileOverlay.classList.remove('open');
}

async function loadProfile() {
    try {
        const res = await fetch('/api/profile');
        if (!res.ok) return;
        const data = await res.json();

        // Google avatar / initials — use server proxy to avoid CORS/referrer blocks
        const avatarEl = document.getElementById('profileAvatarLarge');
        if (data.picture) {
            avatarEl.innerHTML = `<img src="/api/avatar" alt="" style="width:52px;height:52px;object-fit:cover;display:block;border-radius:50%;">`;
        } else {
            avatarEl.innerHTML = `<span class="profile-avatar-large-initials">${(data.nama || '?')[0].toUpperCase()}</span>`;
        }

        document.getElementById('profileGoogleName').textContent  = data.nama  || '';
        document.getElementById('profileGoogleEmail').textContent = data.email || '';

        document.getElementById('pNama').value    = data.nama    || '';
        document.getElementById('pJawatan').value = data.jawatan || '';
        document.getElementById('pStesen').value  = data.stesen  || '';
        document.getElementById('pDaerah').value  = data.daerah  || '';
        document.getElementById('pNegeri').value  = data.negeri  || '';
    } catch (e) {
        console.error('Profile load error:', e);
    }
}

document.getElementById('profileForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('profileSaveBtn');
    const msg = document.getElementById('profileSaveMsg');
    btn.disabled = true;
    btn.textContent = 'Menyimpan...';
    try {
        const res = await fetch('/api/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nama:    document.getElementById('pNama').value.trim(),
                jawatan: document.getElementById('pJawatan').value.trim(),
                stesen:  document.getElementById('pStesen').value.trim(),
                daerah:  document.getElementById('pDaerah').value.trim(),
                negeri:  document.getElementById('pNegeri').value,
            })
        });
        if (res.ok) {
            msg.textContent = I18N[currentLang].profile_saved_ok;
            msg.style.color = '#22c55e';
            setTimeout(() => { msg.textContent = ''; }, 3000);
        } else {
            msg.textContent = I18N[currentLang].profile_saved_fail;
            msg.style.color = '#f87171';
        }
    } catch (e) {
        msg.textContent = I18N[currentLang].profile_conn_err;
        msg.style.color = '#f87171';
    }
    btn.disabled = false;
    btn.textContent = I18N[currentLang].profile_save;
});

if (profileBtn)     profileBtn.addEventListener('click', openProfilePanel);
if (profileCloseBtn) profileCloseBtn.addEventListener('click', closeProfilePanel);
if (profileOverlay)  profileOverlay.addEventListener('click', closeProfilePanel);
