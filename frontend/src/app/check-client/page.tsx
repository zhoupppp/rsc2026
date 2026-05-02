"use client";
import { useEffect, useState } from 'react';

export default function CheckPage() {
  const [data, setData] = useState<string>('Loading...');

  useEffect(() => {
    fetch('http://localhost:8000/api/talents/RSC/613520')
      .then(res => res.text().then(text => ({ status: res.status, text })))
      .then(({ status, text }) => {
        setData(`STATUS: ${status}\nBODY: ${text}`);
      })
      .catch(err => {
        setData(`ERROR: ${err.message}`);
      });
  }, []);

  return (
    <div style={{ whiteSpace: 'pre-wrap', padding: '20px' }} id="output">
      {data}
    </div>
  );
}
