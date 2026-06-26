// src/data/payments.js
export const PAYMENTS = [
  ['Abena Mensah',   'GH-0042', 'GHS 120', 'MoMo',  'Jun 05, 2026', 'Paid',    'bdg-green'],
  ['Kwame Asante',   'GH-0081', 'GHS 120', 'USSD',  'Jun 05, 2026', 'Paid',    'bdg-green'],
  ['Ama Osei',       'GH-0017', 'GHS 120', 'Card',  'Jun 04, 2026', 'Pending', 'bdg-amber'],
  ['Kofi Darko',     'GH-0103', 'GHS 120', 'MoMo',  'Jun 04, 2026', 'Paid',    'bdg-green'],
  ['Akosua Boateng', 'GH-0056', 'GHS 120', 'USSD',  'Jun 03, 2026', 'Failed',  'bdg-red'],
]

// Initial seed — DashboardPage manages live state on top of this
export const MEMBERS_SEED = [
  { id: 'GH-0042', name: 'Abena Mensah',   phone: '055 234 xxxx', region: 'Ashanti',     dues: 'Paid',    score: '87', tier: 'sh' },
  { id: 'GH-0081', name: 'Kwame Asante',   phone: '024 891 xxxx', region: 'Northern',    dues: 'Paid',    score: '74', tier: 'sm' },
  { id: 'GH-0017', name: 'Ama Osei',       phone: '059 441 xxxx', region: 'Gr. Accra',   dues: 'Pending', score: '61', tier: 'sm' },
  { id: 'GH-0103', name: 'Kofi Darko',     phone: '020 773 xxxx', region: 'Brong-Ahafo', dues: 'Paid',    score: '92', tier: 'sh' },
  { id: 'GH-0056', name: 'Akosua Boateng', phone: '026 558 xxxx', region: 'Eastern',     dues: 'Overdue', score: '43', tier: 'sl' },
  { id: 'GH-0128', name: 'Yaw Frimpong',   phone: '050 362 xxxx', region: 'Volta',       dues: 'Paid',    score: '79', tier: 'sm' },
]

// Keep legacy tuple export so Scores/other components still work
export const MEMBERS = MEMBERS_SEED.map(m => [m.name, m.id, m.phone, m.region, m.dues, m.score, m.tier])

export const SCORES = [
  ['Kofi Darko',     'Brong-Ahafo', '95', '88', '90', '92', 'sh'],
  ['Abena Mensah',   'Ashanti',     '90', '85', '88', '87', 'sh'],
  ['Yaw Frimpong',   'Volta',       '82', '76', '78', '79', 'sm'],
  ['Kwame Asante',   'Northern',    '78', '70', '74', '74', 'sm'],
  ['Ama Osei',       'Gr. Accra',   '65', '58', '62', '61', 'sm'],
  ['Akosua Boateng', 'Eastern',     '40', '45', '44', '43', 'sl'],
]
