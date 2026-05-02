import { NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api';

export async function GET() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/talents/RSC/613520`);
    const text = await res.text();
    return new NextResponse(`<html><body><script>console.error("BACKEND_RESULT: ", \`${text.replace(/`/g, '\\`')}\`);</script></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  } catch (err: any) {
    return new NextResponse(`<html><body><script>console.error("BACKEND_ERROR: ", \`${err.message}\`);</script></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}
