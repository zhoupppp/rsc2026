import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function GET() {
  try {
    const { stdout, stderr } = await execAsync('sqlite3 /Users/zhoupeng/Documents/rsc2026/financial_scraper/financial_data_v1.db ".schema rsc_orgs"');
    return new NextResponse(`<html><body><pre>STDOUT:\n${stdout}\n\nSTDERR:\n${stderr}</pre></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  } catch (err: any) {
    return new NextResponse(`<html><body><pre>EXEC_ERROR: \n${err.message}\n\nSTDOUT:\n${err.stdout}\n\nSTDERR:\n${err.stderr}</pre></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}
