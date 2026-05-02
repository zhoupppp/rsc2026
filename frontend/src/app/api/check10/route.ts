import { NextResponse } from 'next/server';
import { API_BASE_URL } from '@/lib/api';

export async function GET() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/talents/RSC/613520`);
    const text = await res.text();
    return new NextResponse(`<html><body><h1>API_RESULT</h1><p id="res">${text}</p></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  } catch (err: any) {
    return new NextResponse(`<html><body><h1>API_ERROR</h1><p id="err">${err.message}</p></body></html>`, {
      headers: { 'Content-Type': 'text/html' }
    });
  }
}
