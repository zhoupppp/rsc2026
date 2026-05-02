import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function GET() {
  try {
    const { stdout, stderr } = await execAsync('python3 /Users/zhoupeng/Documents/rsc2026/test_613520_db.py');
    return new NextResponse(`<html><body><pre>STDOUT:\n${stdout}\n\nSTDERR:\n${stderr}</pre></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  } catch (err: any) {
    return new NextResponse(`<html><body><pre>EXEC_ERROR: \n${err.message}\n\nSTDOUT:\n${err.stdout}\n\nSTDERR:\n${err.stderr}</pre></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}
