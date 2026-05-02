import { NextResponse } from 'next/server';
import { execSync } from 'child_process';

export async function GET() {
  try {
    const output = execSync('python3 -m py_compile /Users/zhoupeng/Documents/rsc2026/backend/main.py', { encoding: 'utf-8' });
    return NextResponse.json({ success: true, output });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message, stderr: error.stderr });
  }
}
