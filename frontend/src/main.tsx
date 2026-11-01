import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './style.css';
import './ui-refinement.css';
import { installDebugRecorder } from './lib/debug-recorder';

installDebugRecorder();

// Open mouse-driven single selects on click, after the opening release has finished.
// Keep keyboard, touch, listboxes and browsers without showPicker on native behavior.
if ('showPicker' in HTMLSelectElement.prototype) {
  const singleSelect = (target: EventTarget | null) =>
    target instanceof HTMLSelectElement && !target.disabled && !target.multiple && target.size <= 1 ? target : null;
  document.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button === 0 && singleSelect(event.target)) event.preventDefault();
  }, true);
  document.addEventListener('click', event => {
    const select = singleSelect(event.target);
    if (!select || event.detail === 0 || !(event instanceof PointerEvent) || event.pointerType !== 'mouse') return;
    event.preventDefault();
    select.focus();
    try { select.showPicker(); } catch { /* Keyboard selection remains available if the browser refuses the popup. */ }
  }, true);
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
