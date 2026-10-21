import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Radar } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  label?: string;
};

export function SearchButton({ className, label = "Buscar ahora" }: Props) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: api.search,
    onSuccess: (data) => {
      toast.success(
        data.run.new > 0
          ? `Búsqueda lista: ${data.run.new} ofertas nuevas de ${data.run.found}.`
          : `Búsqueda lista: ${data.run.found} ofertas revisadas, sin novedades.`,
      );
      queryClient.invalidateQueries();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <button type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending} className={cn("btn-primary", className)}>
      {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radar className="h-4 w-4" />}
      {mutation.isPending ? "Buscando..." : label}
    </button>
  );
}
