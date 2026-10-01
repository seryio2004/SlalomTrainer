import { execFileSync } from 'node:child_process'
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const output = mkdtempSync(join(tmpdir(), 'teitraining-load-'))
try {
  writeFileSync(join(output, 'package.json'), '{"type":"commonjs"}')
  execFileSync(process.execPath, [
    'node_modules/typescript/bin/tsc',
    'src/training/load.ts',
    '--rootDir', '.',
    '--outDir', output,
    '--target', 'ES2022',
    '--module', 'commonjs',
    '--moduleResolution', 'node',
    '--skipLibCheck',
    '--strict',
  ], { stdio: 'inherit' })
  mkdirSync(join(output, 'tests'))
  copyFileSync('tests/load.test.cjs', join(output, 'tests/load.test.cjs'))
  execFileSync(process.execPath, ['--test', join(output, 'tests/load.test.cjs')], {
    stdio: 'inherit',
    env: { ...process.env, TZ: 'Europe/Madrid' },
  })
} finally {
  rmSync(output, { recursive: true, force: true })
}
