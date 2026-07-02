'use client';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import type { ClimberProfile, ExperienceLevel, ClimbingStyle, HandDominance } from '@/types';
import { Button } from '@/components/ui/Button';

const profileSchema = z.object({
  name: z.string().min(1, 'Name required'),
  height_cm: z.number().min(100).max(250),
  weight_kg: z.number().min(30).max(200),
  wingspan_cm: z.number().min(100).max(260),
  arm_length_cm: z.number().min(40).max(120),
  forearm_length_cm: z.number().min(20).max(60),
  leg_length_cm: z.number().min(60).max(140),
  torso_length_cm: z.number().min(30).max(80),
  shoulder_mobility_deg: z.number().min(0).max(180),
  hip_mobility_deg: z.number().min(0).max(180),
  ankle_dorsiflexion_deg: z.number().min(-10).max(40),
  hamstring_flexibility_score: z.number().min(0).max(1),
  core_strength_score: z.number().min(0).max(1),
  finger_strength_score: z.number().min(0).max(1),
  pinch_strength_score: z.number().min(0).max(1),
  crimp_strength_score: z.number().min(0).max(1),
  sloper_ability_score: z.number().min(0).max(1),
  dynamic_comfort_score: z.number().min(0).max(1),
  fear_of_dynamic: z.number().min(0).max(1),
  preferred_style: z.enum(['static', 'dynamic', 'balanced', 'powerful', 'technical', 'slopey', 'crimpy', 'compression']),
  experience_level: z.enum(['beginner', 'intermediate', 'advanced', 'expert', 'elite']),
  indoor_grade_v: z.number().min(0).max(17).int(),
  hand_dominance: z.enum(['left', 'right', 'ambidextrous']),
  foot_dominance: z.enum(['left', 'right', 'ambidextrous']),
});

type ProfileFormData = z.infer<typeof profileSchema>;

interface ProfileFormProps {
  defaultValues?: Partial<ClimberProfile>;
  onSubmit: (data: ProfileFormData) => void;
  isLoading?: boolean;
}

interface ScoreSliderProps {
  label: string;
  name: keyof ProfileFormData;
  register: ReturnType<typeof useForm<ProfileFormData>>['register'];
  watch: ReturnType<typeof useForm<ProfileFormData>>['watch'];
  description?: string;
}

function ScoreSlider({ label, name, register, watch, description }: ScoreSliderProps) {
  const value = watch(name as any) as number;
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs text-slate-400">{label}</label>
        <span className="text-xs font-mono text-accent-400">
          {((value || 0) * 100).toFixed(0)}%
        </span>
      </div>
      {description && <p className="text-xs text-slate-600 mb-1">{description}</p>}
      <input
        type="range"
        min="0"
        max="1"
        step="0.05"
        {...register(name as any, { valueAsNumber: true })}
        className="w-full accent-accent-500"
      />
    </div>
  );
}

interface NumberInputProps {
  label: string;
  name: keyof ProfileFormData;
  register: ReturnType<typeof useForm<ProfileFormData>>['register'];
  errors: ReturnType<typeof useForm<ProfileFormData>>['formState']['errors'];
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
}

function NumberInput({ label, name, register, errors, unit, min, max, step = 1 }: NumberInputProps) {
  const error = errors[name];
  return (
    <div>
      <label className="text-xs text-slate-400 block mb-1">
        {label} {unit && <span className="text-slate-600">({unit})</span>}
      </label>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        {...register(name as any, { valueAsNumber: true })}
        className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
      />
      {error && <p className="text-xs text-red-400 mt-1">{error.message as string}</p>}
    </div>
  );
}

export function ProfileForm({ defaultValues, onSubmit, isLoading }: ProfileFormProps) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      name: defaultValues?.name ?? 'My Profile',
      height_cm: defaultValues?.height_cm ?? 170,
      weight_kg: defaultValues?.weight_kg ?? 68,
      wingspan_cm: defaultValues?.wingspan_cm ?? 172,
      arm_length_cm: defaultValues?.arm_length_cm ?? 75,
      forearm_length_cm: defaultValues?.forearm_length_cm ?? 35,
      leg_length_cm: defaultValues?.leg_length_cm ?? 88,
      torso_length_cm: defaultValues?.torso_length_cm ?? 55,
      shoulder_mobility_deg: defaultValues?.shoulder_mobility_deg ?? 160,
      hip_mobility_deg: defaultValues?.hip_mobility_deg ?? 95,
      ankle_dorsiflexion_deg: defaultValues?.ankle_dorsiflexion_deg ?? 15,
      hamstring_flexibility_score: defaultValues?.hamstring_flexibility_score ?? 0.5,
      core_strength_score: defaultValues?.core_strength_score ?? 0.5,
      finger_strength_score: defaultValues?.finger_strength_score ?? 0.5,
      pinch_strength_score: defaultValues?.pinch_strength_score ?? 0.45,
      crimp_strength_score: defaultValues?.crimp_strength_score ?? 0.5,
      sloper_ability_score: defaultValues?.sloper_ability_score ?? 0.4,
      dynamic_comfort_score: defaultValues?.dynamic_comfort_score ?? 0.5,
      fear_of_dynamic: defaultValues?.fear_of_dynamic ?? 0.25,
      preferred_style: (defaultValues?.preferred_style ?? 'balanced') as ClimbingStyle,
      experience_level: (defaultValues?.experience_level ?? 'intermediate') as ExperienceLevel,
      indoor_grade_v: defaultValues?.indoor_grade_v ?? 5,
      hand_dominance: (defaultValues?.hand_dominance ?? 'right') as HandDominance,
      foot_dominance: (defaultValues?.foot_dominance ?? 'right') as HandDominance,
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Basic info */}
      <section>
        <h3 className="text-sm font-semibold text-slate-300 mb-3 pb-1 border-b border-slate-700">
          Basic Info
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Name</label>
            <input
              {...register('name')}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Indoor Grade (V-scale)</label>
            <input
              type="number"
              min={0}
              max={17}
              {...register('indoor_grade_v', { valueAsNumber: true })}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Experience Level</label>
            <select
              {...register('experience_level')}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500"
            >
              {['beginner', 'intermediate', 'advanced', 'expert', 'elite'].map((v) => (
                <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Preferred Style</label>
            <select
              {...register('preferred_style')}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500"
            >
              {['static', 'dynamic', 'balanced', 'powerful', 'technical', 'slopey', 'crimpy', 'compression'].map((v) => (
                <option key={v} value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Anthropometrics */}
      <section>
        <h3 className="text-sm font-semibold text-slate-300 mb-3 pb-1 border-b border-slate-700">
          Measurements
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <NumberInput label="Height" name="height_cm" register={register} errors={errors} unit="cm" min={100} max={250} />
          <NumberInput label="Weight" name="weight_kg" register={register} errors={errors} unit="kg" min={30} max={200} />
          <NumberInput label="Wingspan" name="wingspan_cm" register={register} errors={errors} unit="cm" min={100} max={260} />
          <NumberInput label="Arm Length" name="arm_length_cm" register={register} errors={errors} unit="cm" min={40} max={120} />
          <NumberInput label="Forearm Length" name="forearm_length_cm" register={register} errors={errors} unit="cm" min={20} max={60} />
          <NumberInput label="Leg Length" name="leg_length_cm" register={register} errors={errors} unit="cm" min={60} max={140} />
          <NumberInput label="Torso Length" name="torso_length_cm" register={register} errors={errors} unit="cm" min={30} max={80} />
          <NumberInput label="Shoulder Mobility" name="shoulder_mobility_deg" register={register} errors={errors} unit="°" min={0} max={180} />
          <NumberInput label="Hip Mobility" name="hip_mobility_deg" register={register} errors={errors} unit="°" min={0} max={180} />
        </div>
      </section>

      {/* Strength & Skills */}
      <section>
        <h3 className="text-sm font-semibold text-slate-300 mb-3 pb-1 border-b border-slate-700">
          Strength & Skills (0–100%)
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ScoreSlider label="Core Strength" name="core_strength_score" register={register} watch={watch} />
          <ScoreSlider label="Finger Strength" name="finger_strength_score" register={register} watch={watch} />
          <ScoreSlider label="Crimp Strength" name="crimp_strength_score" register={register} watch={watch} />
          <ScoreSlider label="Pinch Strength" name="pinch_strength_score" register={register} watch={watch} />
          <ScoreSlider label="Sloper Ability" name="sloper_ability_score" register={register} watch={watch} />
          <ScoreSlider label="Dynamic Comfort" name="dynamic_comfort_score" register={register} watch={watch} />
          <ScoreSlider label="Hamstring Flexibility" name="hamstring_flexibility_score" register={register} watch={watch} />
          <ScoreSlider label="Fear of Dynamic" name="fear_of_dynamic" register={register} watch={watch} description="0% = fearless, 100% = refuses all dynos" />
        </div>
      </section>

      {/* Dominance */}
      <section>
        <h3 className="text-sm font-semibold text-slate-300 mb-3 pb-1 border-b border-slate-700">
          Dominance
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Hand Dominance</label>
            <select
              {...register('hand_dominance')}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500"
            >
              <option value="right">Right</option>
              <option value="left">Left</option>
              <option value="ambidextrous">Ambidextrous</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-400 block mb-1">Foot Dominance</label>
            <select
              {...register('foot_dominance')}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-accent-500"
            >
              <option value="right">Right</option>
              <option value="left">Left</option>
              <option value="ambidextrous">Ambidextrous</option>
            </select>
          </div>
        </div>
      </section>

      <Button type="submit" loading={isLoading} size="lg" className="w-full">
        Save Profile
      </Button>
    </form>
  );
}
