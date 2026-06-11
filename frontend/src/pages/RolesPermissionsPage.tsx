import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Plus, Save, ShieldCheck, Trash2, UserCog } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Alert } from "../components/ui/Alert";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Skeleton } from "../components/ui/LoadingSpinner";
import {
  assignRolesToUser,
  createRole,
  deleteRole,
  fetchPermissions,
  fetchRoles,
  fetchUsers,
  updateRole
} from "../services/api";
import type { PermissionResource, RoleResource } from "../services/api";

type RoleForm = {
  name: string;
  description: string;
  permissionIds: number[];
};

const emptyForm: RoleForm = {
  name: "",
  description: "",
  permissionIds: []
};

export function RolesPermissionsPage() {
  const queryClient = useQueryClient();
  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: fetchRoles });
  const permissionsQuery = useQuery({ queryKey: ["permissions"], queryFn: fetchPermissions });
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: fetchUsers });
  const [selectedRoleId, setSelectedRoleId] = useState<number | "new">("new");
  const [form, setForm] = useState<RoleForm>(emptyForm);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedUserRoleId, setSelectedUserRoleId] = useState<number | null>(null);

  const selectedRole = useMemo(
    () => rolesQuery.data?.find((role) => role.id === selectedRoleId),
    [rolesQuery.data, selectedRoleId]
  );

  useEffect(() => {
    if (selectedRole) {
      setForm({
        name: selectedRole.name,
        description: selectedRole.description,
        permissionIds: selectedRole.permissions.map((permission) => permission.id)
      });
      return;
    }
    setForm(emptyForm);
  }, [selectedRole]);

  useEffect(() => {
    if (!usersQuery.data?.length || selectedUserId !== null) return;
    const user = usersQuery.data[0];
    setSelectedUserId(user.id);
  }, [selectedUserId, usersQuery.data]);

  useEffect(() => {
    const user = usersQuery.data?.find((item) => item.id === selectedUserId);
    const role = rolesQuery.data?.find((item) => item.slug === user?.role);
    setSelectedUserRoleId(role?.id ?? rolesQuery.data?.[0]?.id ?? null);
  }, [rolesQuery.data, selectedUserId, usersQuery.data]);

  const invalidateRbac = () => {
    queryClient.invalidateQueries({ queryKey: ["roles"] });
    queryClient.invalidateQueries({ queryKey: ["users"] });
    queryClient.invalidateQueries({ queryKey: ["current-user"] });
    queryClient.invalidateQueries({ queryKey: ["navigation"] });
  };

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload = {
        name: form.name,
        description: form.description,
        permission_ids: form.permissionIds
      };
      return selectedRole ? updateRole(selectedRole.id, payload) : createRole(payload);
    },
    onSuccess: (role) => {
      setSelectedRoleId(role.id);
      invalidateRbac();
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRole,
    onSuccess: () => {
      setSelectedRoleId("new");
      invalidateRbac();
    }
  });

  const assignMutation = useMutation({
    mutationFn: () => {
      if (!selectedUserId || !selectedUserRoleId) {
        throw new Error("Select a user and role");
      }
      return assignRolesToUser(selectedUserId, [selectedUserRoleId]);
    },
    onSuccess: invalidateRbac
  });

  const loading = rolesQuery.isLoading || permissionsQuery.isLoading || usersQuery.isLoading;
  const error = rolesQuery.isError || permissionsQuery.isError || usersQuery.isError;
  const roles = rolesQuery.data ?? [];
  const permissions = permissionsQuery.data ?? [];
  const assignedCount = form.permissionIds.length;

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <ShieldCheck size={14} aria-hidden />
              Administration
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Roles & Permissions</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Manage RBAC roles, permission assignments, and each user's access role.
            </p>
          </div>
          <div className="grid min-w-[168px] gap-1 rounded-[8px] border border-white/10 bg-white/10 p-3 text-right backdrop-blur-md dark:bg-white/5">
            <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">Permissions</span>
            <span className="text-2xl font-black text-slate-950 dark:text-white">{permissions.length}</span>
          </div>
        </div>
      </Card>

      {error ? <Alert tone="error">Unable to load roles and permissions.</Alert> : null}
      {saveMutation.isError ? <Alert tone="error">Unable to save this role. Check the name and permissions.</Alert> : null}
      {deleteMutation.isError ? <Alert tone="error">Unable to delete this role. System roles are protected.</Alert> : null}
      {assignMutation.isError ? <Alert tone="error">Unable to assign this role to the selected user.</Alert> : null}
      {saveMutation.isSuccess ? <Alert tone="success">Role saved.</Alert> : null}
      {assignMutation.isSuccess ? <Alert tone="success">User role updated.</Alert> : null}

      {loading ? (
        <Skeleton className="h-[560px]" />
      ) : (
        <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <RoleList roles={roles} selectedRoleId={selectedRoleId} onSelect={setSelectedRoleId} />

          <div className="grid gap-4">
            <Card className="p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="grid flex-1 gap-3">
                  <Input
                    label="Role name"
                    value={form.name}
                    onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
                  />
                  <Input
                    label="Description"
                    value={form.description}
                    onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button icon={Save} loading={saveMutation.isPending} disabled={!form.name.trim()} onClick={() => saveMutation.mutate()}>
                    {selectedRole ? "Save role" : "Create role"}
                  </Button>
                  {selectedRole ? (
                    <Button
                      icon={Trash2}
                      variant="danger"
                      disabled={selectedRole.is_system}
                      loading={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(selectedRole.id)}
                    >
                      Delete
                    </Button>
                  ) : null}
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                <Badge tone="info">{assignedCount} assigned</Badge>
                {selectedRole?.is_system ? <Badge tone="neutral">System role</Badge> : null}
              </div>
            </Card>

            <Card className="p-5">
              <div className="mb-4 flex items-center gap-2">
                <KeyRound size={18} className="text-cyan-600 dark:text-cyan-200" aria-hidden />
                <h2 className="text-lg font-black text-slate-950 dark:text-white">Permission Matrix</h2>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                {permissions.map((permission) => (
                  <PermissionToggle
                    key={permission.id}
                    permission={permission}
                    checked={form.permissionIds.includes(permission.id)}
                    onChange={(checked) => {
                      setForm((current) => ({
                        ...current,
                        permissionIds: checked
                          ? Array.from(new Set([...current.permissionIds, permission.id]))
                          : current.permissionIds.filter((id) => id !== permission.id)
                      }));
                    }}
                  />
                ))}
              </div>
            </Card>

            <Card className="p-5">
              <div className="mb-4 flex items-center gap-2">
                <UserCog size={18} className="text-cyan-600 dark:text-cyan-200" aria-hidden />
                <h2 className="text-lg font-black text-slate-950 dark:text-white">Assign Role To User</h2>
              </div>
              <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-end">
                <Select
                  label="User"
                  value={selectedUserId ?? ""}
                  options={(usersQuery.data ?? []).map((user) => ({
                    label: `${user.full_name} (${user.email})`,
                    value: String(user.id)
                  }))}
                  onChange={(event) => setSelectedUserId(Number(event.target.value))}
                />
                <Select
                  label="Role"
                  value={selectedUserRoleId ?? ""}
                  options={roles.map((role) => ({ label: role.name, value: String(role.id) }))}
                  onChange={(event) => setSelectedUserRoleId(Number(event.target.value))}
                />
                <Button icon={UserCog} loading={assignMutation.isPending} onClick={() => assignMutation.mutate()}>
                  Assign
                </Button>
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

function RoleList({
  roles,
  selectedRoleId,
  onSelect
}: {
  roles: RoleResource[];
  selectedRoleId: number | "new";
  onSelect: (id: number | "new") => void;
}) {
  return (
    <Card className="p-3">
      <button
        type="button"
        onClick={() => onSelect("new")}
        className="mb-2 flex min-h-11 w-full items-center gap-3 rounded-[8px] px-3 text-left text-sm font-bold text-slate-700 transition hover:bg-white/15 dark:text-white/70"
      >
        <Plus size={16} aria-hidden />
        Create role
      </button>
      <div className="grid gap-1">
        {roles.map((role) => (
          <button
            key={role.id}
            type="button"
            onClick={() => onSelect(role.id)}
            className={`rounded-[8px] px-3 py-3 text-left transition ${
              selectedRoleId === role.id
                ? "bg-cyan-400/20 text-cyan-800 ring-1 ring-cyan-300/30 dark:text-cyan-100"
                : "text-slate-700 hover:bg-white/10 dark:text-white/65"
            }`}
          >
            <span className="block text-sm font-black">{role.name}</span>
            <span className="mt-1 block text-xs font-semibold text-slate-500 dark:text-white/40">
              {role.permissions.length} permissions
            </span>
          </button>
        ))}
      </div>
    </Card>
  );
}

function PermissionToggle({
  permission,
  checked,
  onChange
}: {
  permission: PermissionResource;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex min-h-[86px] cursor-pointer gap-3 rounded-[8px] border border-white/10 bg-white/10 p-3 backdrop-blur-md transition hover:bg-white/15 dark:bg-white/5">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 size-4 accent-cyan-500"
      />
      <span>
        <span className="block text-sm font-black text-slate-950 dark:text-white">{permission.name}</span>
        <span className="mt-1 block text-xs font-medium leading-5 text-slate-600 dark:text-white/50">
          {permission.description}
        </span>
      </span>
    </label>
  );
}
