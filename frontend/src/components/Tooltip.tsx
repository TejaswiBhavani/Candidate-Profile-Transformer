import { useState } from 'react';
import './Tooltip.css';

interface TooltipProps {
  text: string;
}

export function Tooltip({ text }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span 
      className="tooltip-container"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onClick={() => setVisible(!visible)}
    >
      <span className="tooltip-icon">ⓘ</span>
      {visible && (
        <div className="tooltip-box">
          {text}
        </div>
      )}
    </span>
  );
}
