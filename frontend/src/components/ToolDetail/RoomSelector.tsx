import React from 'react';

const ROOM_TYPES = [
  { value: 'living_room', label: '客厅' },
  { value: 'bedroom', label: '卧室' },
  { value: 'study', label: '书房' },
  { value: 'kitchen', label: '厨房' },
  { value: 'bathroom', label: '卫生间' },
  { value: 'dining_room', label: '餐厅' },
  { value: 'entrance', label: '玄关' },
  { value: 'balcony', label: '阳台' },
  { value: 'kids_room', label: '儿童房' },
  { value: 'closet', label: '衣帽间' },
];

interface RoomSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

const RoomSelector: React.FC<RoomSelectorProps> = ({ value, onChange }) => {
  return (
    <div className="flex flex-col gap-3">
      <span className="text-white/60 text-xs">房间类型</span>
      <div className="grid grid-cols-5 gap-2">
        {ROOM_TYPES.map((room) => (
          <button
            key={room.value}
            onClick={() => onChange(room.value)}
            className={`h-8 text-xs transition-colors border ${
              value === room.value
                ? 'bg-[#E2E85C] text-black border-[#E2E85C]'
                : 'bg-white/5 text-white/60 border-white/10 hover:bg-white/10 hover:text-white'
            }`}
          >
            {room.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default RoomSelector;
