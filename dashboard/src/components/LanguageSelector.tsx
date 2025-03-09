import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from './ui/select';

interface LanguageSelectorProps {
  currentLanguage: string;
  onChange: (language: string) => void;
  disabled?: boolean;
}

export default function LanguageSelector({ currentLanguage, onChange, disabled = false }: LanguageSelectorProps) {
  return (
    <div className="flex items-center">
      <span className="mr-2 text-sm font-medium">Language:</span>
      <Select 
        value={currentLanguage} 
        onValueChange={onChange}
        disabled={disabled}
      >
        <SelectTrigger className="w-32 h-8">
          <SelectValue placeholder="Select language" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="python">Python</SelectItem>
          <SelectItem value="javascript">JavaScript</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}