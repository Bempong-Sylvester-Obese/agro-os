// @vitest-environment node
/**
 * Guard for the API-only tenancy decision (docs/architecture/tenancy-decision.md).
 *
 * Tenant isolation is enforced only by the FastAPI layer, so the browser bundle
 * must never contain a way to reach the database directly: no Supabase/Postgres
 * SDK, no database URL, and no VITE_SUPABASE_* / VITE_DATABASE_* variables.
 * If a legitimate need arises, update the decision record first.
 */
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs'
import { join, resolve, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const FRONTEND_ROOT = resolve(__dirname, '..', '..')
const SRC_ROOT = join(FRONTEND_ROOT, 'src')

const FORBIDDEN_SOURCE_PATTERNS = [
  { name: 'Supabase client import', regex: /['"]@supabase\/[\w-]+['"]/ },
  { name: 'Postgres driver import', regex: /['"](pg|postgres|postgres-js|@neondatabase\/serverless)['"]/ },
  { name: 'Postgres connection string', regex: /postgres(ql)?:\/\/[^\s'"`]+/ },
  { name: 'Supabase env variable', regex: /VITE_SUPABASE_[A-Z_]+/ },
  { name: 'Database env variable', regex: /VITE_(DATABASE|DB)_[A-Z_]+/ },
  { name: 'Service-role key reference', regex: /service_role/i },
]

const FORBIDDEN_DEPENDENCIES = [
  /^@supabase\//,
  /^pg$/,
  /^postgres$/,
  /^@neondatabase\//,
  /^drizzle-orm$/,
  /^@prisma\//,
]

const SOURCE_EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'])

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      walk(full, out)
      continue
    }
    const ext = full.slice(full.lastIndexOf('.'))
    if (SOURCE_EXTENSIONS.has(ext)) out.push(full)
  }
  return out
}

function isThisGuard(file) {
  return resolve(file) === resolve(__filename)
}

describe('API-only tenancy: the client never holds database access', () => {
  const sourceFiles = walk(SRC_ROOT).filter((file) => !isThisGuard(file))

  it('scans a non-trivial amount of source', () => {
    expect(sourceFiles.length).toBeGreaterThan(10)
  })

  it('contains no database SDK imports, connection strings, or DB env variables', () => {
    const violations = []
    for (const file of sourceFiles) {
      const text = readFileSync(file, 'utf8')
      for (const { name, regex } of FORBIDDEN_SOURCE_PATTERNS) {
        const match = text.match(regex)
        if (match) {
          violations.push(`${relative(FRONTEND_ROOT, file)}: ${name} (${match[0]})`)
        }
      }
    }
    expect(violations).toEqual([])
  })

  it('declares no database client packages in package.json', () => {
    const pkg = JSON.parse(readFileSync(join(FRONTEND_ROOT, 'package.json'), 'utf8'))
    const declared = Object.keys({ ...pkg.dependencies, ...pkg.devDependencies })
    const offenders = declared.filter((dep) => FORBIDDEN_DEPENDENCIES.some((re) => re.test(dep)))
    expect(offenders).toEqual([])
  })

  it('only documents API_URL-style variables in .env.example', () => {
    const envExample = join(FRONTEND_ROOT, '.env.example')
    if (!existsSync(envExample)) return
    const keys = readFileSync(envExample, 'utf8')
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line && !line.startsWith('#'))
      .map((line) => line.split('=')[0])
    const offenders = keys.filter((key) => /SUPABASE|DATABASE|DB_|SERVICE_ROLE|SECRET/i.test(key))
    expect(offenders).toEqual([])
  })
})
