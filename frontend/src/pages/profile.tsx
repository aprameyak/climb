import type { NextPage } from 'next';
import { useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { ProfileForm } from '@/components/profile/ProfileForm';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { useProfiles, useCreateProfile, useUpdateProfile } from '@/hooks/useProfile';
import { useAppStore } from '@/store/useAppStore';
import type { ClimberProfile } from '@/types';
import { Edit2, Plus, User } from 'lucide-react';

type Mode = 'list' | 'create' | 'edit';

const ProfilePage: NextPage = () => {
  const [mode, setMode] = useState<Mode>('list');
  const [editingProfile, setEditingProfile] = useState<ClimberProfile | null>(null);

  const { data: profiles, isLoading } = useProfiles();
  const { mutate: createProfile, isPending: isCreating } = useCreateProfile();
  const { mutate: updateProfile, isPending: isUpdating } = useUpdateProfile();
  const { currentProfile, setCurrentProfile } = useAppStore();

  const handleCreate = (data: any) => {
    createProfile(
      {
        ...data,
        injuries: [],
      },
      {
        onSuccess: () => setMode('list'),
      }
    );
  };

  const handleUpdate = (data: any) => {
    if (!editingProfile) return;
    updateProfile(
      { id: editingProfile.id, updates: data },
      { onSuccess: () => { setMode('list'); setEditingProfile(null); } }
    );
  };

  if (isLoading) return <PageLayout><LoadingSpinner size="lg" /></PageLayout>;

  if (mode === 'create') {
    return (
      <PageLayout title="Create Profile" maxWidth="2xl">
        <button
          onClick={() => setMode('list')}
          className="text-sm text-slate-500 hover:text-slate-300 mb-4 flex items-center gap-1"
        >
          ← Back to profiles
        </button>
        <Card>
          <ProfileForm onSubmit={handleCreate} isLoading={isCreating} />
        </Card>
      </PageLayout>
    );
  }

  if (mode === 'edit' && editingProfile) {
    return (
      <PageLayout title="Edit Profile" maxWidth="2xl">
        <button
          onClick={() => { setMode('list'); setEditingProfile(null); }}
          className="text-sm text-slate-500 hover:text-slate-300 mb-4 flex items-center gap-1"
        >
          ← Back to profiles
        </button>
        <Card>
          <ProfileForm
            defaultValues={editingProfile}
            onSubmit={handleUpdate}
            isLoading={isUpdating}
          />
        </Card>
      </PageLayout>
    );
  }

  return (
    <PageLayout title="Climber Profiles" maxWidth="2xl">
      <div className="space-y-4">
        <div className="flex justify-end">
          <Button
            onClick={() => setMode('create')}
            leftIcon={<Plus size={16} />}
          >
            New Profile
          </Button>
        </div>

        {!profiles || profiles.length === 0 ? (
          <EmptyState
            icon={<User size={48} />}
            title="No profiles yet"
            description="Create a climber profile to get personalized beta adapted to your body and abilities"
            action={
              <Button onClick={() => setMode('create')} leftIcon={<Plus size={16} />}>
                Create Profile
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {profiles.map((profile) => {
              const isActive = currentProfile?.id === profile.id;
              return (
                <Card
                  key={profile.id}
                  variant={isActive ? 'highlighted' : 'default'}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-white">{profile.name}</h3>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="accent">V{profile.indoor_grade_v}</Badge>
                        <Badge variant="muted">{profile.experience_level}</Badge>
                        {isActive && <Badge variant="success">Active</Badge>}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => { setEditingProfile(profile); setMode('edit'); }}
                      leftIcon={<Edit2 size={13} />}
                    >
                      Edit
                    </Button>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs mb-3">
                    <div>
                      <div className="text-slate-500">Height</div>
                      <div className="text-slate-300">{profile.height_cm}cm</div>
                    </div>
                    <div>
                      <div className="text-slate-500">Wingspan</div>
                      <div className="text-slate-300">{profile.wingspan_cm}cm</div>
                    </div>
                    <div>
                      <div className="text-slate-500">Ape Index</div>
                      <div className={profile.ape_index >= 0 ? 'text-green-400' : 'text-slate-300'}>
                        {profile.ape_index > 0 ? '+' : ''}{profile.ape_index}cm
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">Style</div>
                      <div className="text-slate-300 capitalize">{profile.preferred_style}</div>
                    </div>
                    <div>
                      <div className="text-slate-500">Fingers</div>
                      <div className="text-slate-300">{(profile.finger_strength_score * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div className="text-slate-500">Dynamic</div>
                      <div className="text-slate-300">{(profile.dynamic_comfort_score * 100).toFixed(0)}%</div>
                    </div>
                  </div>

                  {profile.injuries.length > 0 && (
                    <div className="text-xs text-yellow-500 mb-3">
                      {profile.injuries.length} active injury restriction{profile.injuries.length !== 1 ? 's' : ''}
                    </div>
                  )}

                  <Button
                    variant={isActive ? 'ghost' : 'secondary'}
                    size="sm"
                    onClick={() => setCurrentProfile(isActive ? null : profile)}
                    className="w-full"
                  >
                    {isActive ? 'Deselect' : 'Use This Profile'}
                  </Button>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </PageLayout>
  );
};

export default ProfilePage;
