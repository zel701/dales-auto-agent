"use client";

import { useState } from "react";

type Option = {
  label: string;
  value: string;
  hex?: string;
  sublabel?: string;
  disabled?: boolean;
};

type SingleProps = {
  options: Option[];
  onSelect: (value: string) => void;
  comingSoon?: Option[];
  multiSelect?: false;
};

type MultiProps = {
  options: Option[];
  onContinue: (values: string[]) => void;
  comingSoon?: Option[];
  multiSelect: true;
};

type Props = SingleProps | MultiProps;

export function OptionGrid(props: Props) {
  if (props.multiSelect) {
    return (
      <MultiOptionGrid
        options={props.options}
        onContinue={props.onContinue}
        comingSoon={props.comingSoon}
      />
    );
  }
  return (
    <SingleOptionGrid
      options={props.options}
      onSelect={props.onSelect}
      comingSoon={props.comingSoon}
    />
  );
}

function SingleOptionGrid({
  options,
  onSelect,
  comingSoon,
}: {
  options: Option[];
  onSelect: (value: string) => void;
  comingSoon?: Option[];
}) {
  const [selected, setSelected] = useState<string | null>(null);

  const handleSelect = (value: string) => {
    setSelected(value);
    setTimeout(() => onSelect(value), 150);
  };

  return (
    <div>
      <Grid
        options={options}
        isSelected={(v) => selected === v}
        onClick={handleSelect}
      />
      <ComingSoon options={comingSoon} />
    </div>
  );
}

function MultiOptionGrid({
  options,
  onContinue,
  comingSoon,
}: {
  options: Option[];
  onContinue: (values: string[]) => void;
  comingSoon?: Option[];
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const toggle = (value: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  const canContinue = selected.size > 0;

  return (
    <div>
      <Grid
        options={options}
        isSelected={(v) => selected.has(v)}
        onClick={toggle}
      />
      <ComingSoon options={comingSoon} />
      <div className="mt-8 flex justify-center">
        <button
          onClick={() => onContinue([...selected])}
          disabled={!canContinue}
          className={`rounded-lg px-8 py-3 text-base font-semibold transition-all duration-200 ${
            canContinue
              ? "bg-pink text-white hover:bg-pink-dark"
              : "cursor-not-allowed bg-gray-200 text-gray-400"
          }`}
        >
          Continue
        </button>
      </div>
    </div>
  );
}

function Grid({
  options,
  isSelected,
  onClick,
}: {
  options: Option[];
  isSelected: (value: string) => boolean;
  onClick: (value: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => onClick(option.value)}
          className={`flex items-center gap-3 rounded-lg border-2 px-4 py-3 text-left text-sm font-medium transition-all duration-200 hover:scale-[1.03] hover:border-pink sm:text-base ${
            isSelected(option.value)
              ? "border-pink bg-pink text-white"
              : "border-gray-100 bg-white text-dark hover:shadow-md"
          }`}
        >
          {option.hex && (
            <span
              className="inline-block h-5 w-5 shrink-0 rounded-full border border-gray-200"
              style={{ backgroundColor: option.hex }}
            />
          )}
          <span className="flex flex-col">
            {option.label}
            {option.sublabel && (
              <span
                className={`text-xs font-normal ${
                  isSelected(option.value) ? "text-white/75" : "text-gray-400"
                }`}
              >
                {option.sublabel}
              </span>
            )}
          </span>
        </button>
      ))}
    </div>
  );
}

function ComingSoon({ options }: { options?: Option[] }) {
  if (!options || options.length === 0) return null;
  return (
    <>
      <div className="mt-8 mb-4 flex items-center gap-3">
        <div className="h-px flex-1 bg-gray-200" />
        <span className="text-xs font-semibold uppercase tracking-widest text-gray-300">
          Coming Soon
        </span>
        <div className="h-px flex-1 bg-gray-200" />
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {options.map((option) => (
          <div
            key={option.value}
            className="flex cursor-not-allowed items-center gap-3 rounded-lg border-2 border-gray-100 bg-white px-4 py-3 text-left text-sm font-medium opacity-40 sm:text-base"
          >
            {option.label}
          </div>
        ))}
      </div>
    </>
  );
}
