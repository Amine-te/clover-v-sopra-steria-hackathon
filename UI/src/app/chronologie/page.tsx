"use client";

import { useMemo, useState } from "react";
import { ArrowUpDown, CalendarRange, FunnelX } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { TimelineItem } from "@/components/observations";
import { CATEGORY_ICON } from "@/components/icons";
import { Button, Chip, EmptyState, Segmented } from "@/components/ui";
import { CATEGORY_ORDER, CATEGORY_SHORT } from "@/lib/labels";
import { addDays, dayKey, plural, relativeDay, startOfDay } from "@/lib/format";
import type { Category, Observation, Source } from "@/lib/types";
import { SUBJECT } from "@/mocks/people";
import { useStore } from "@/state/store";

type Period = "1" | "7" | "30";
type SourceFilter = "all" | Source;

const PAGE_DAYS = 7;

export default function TimelinePage() {
  const { state } = useStore();
  const [period, setPeriod] = useState<Period>("7");
  const [source, setSource] = useState<SourceFilter>("all");
  const [categories, setCategories] = useState<Category[]>([]);
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [newestFirst, setNewestFirst] = useState(true);
  const [visibleDays, setVisibleDays] = useState(PAGE_DAYS);

  const filtered = useMemo(() => {
    const from = addDays(startOfDay(new Date()), -(Number(period) - 1)).getTime();
    return state.observations.filter(
      (o) =>
        new Date(o.timestamp).getTime() >= from &&
        (source === "all" || o.source === source) &&
        (categories.length === 0 || categories.includes(o.category)) &&
        (!flaggedOnly || o.severity !== "info"),
    );
  }, [state.observations, period, source, categories, flaggedOnly]);

  const groups = useMemo(() => {
    const map = new Map<string, Observation[]>();
    for (const o of filtered) {
      const k = dayKey(o.timestamp);
      map.set(k, [...(map.get(k) ?? []), o]);
    }
    const days = [...map.entries()].map(([day, list]) => ({
      day,
      list: list.sort((a, b) => (newestFirst ? b.timestamp.localeCompare(a.timestamp) : a.timestamp.localeCompare(b.timestamp))),
    }));
    days.sort((a, b) => (newestFirst ? b.day.localeCompare(a.day) : a.day.localeCompare(b.day)));
    return days;
  }, [filtered, newestFirst]);

  const hasFilters = source !== "all" || categories.length > 0 || flaggedOnly;
  const resetFilters = () => {
    setSource("all");
    setCategories([]);
    setFlaggedOnly(false);
  };

  const toggleCategory = (c: Category) => {
    setVisibleDays(PAGE_DAYS);
    setCategories((list) => (list.includes(c) ? list.filter((x) => x !== c) : [...list, c]));
  };

  return (
    <>
      <PageHeader title="Frise chronologique" eyebrow={`${SUBJECT.firstName} ${SUBJECT.lastName}`} subtitle="Les faits consignés, dans l'ordre où ils se sont produits." />

      <div className="filters">
        <Segmented<Period>
          label="Période"
          value={period}
          onChange={(v) => {
            setPeriod(v);
            setVisibleDays(PAGE_DAYS);
          }}
          options={[
            { value: "1", label: "Aujourd'hui" },
            { value: "7", label: "7 jours" },
            { value: "30", label: "30 jours" },
          ]}
        />
        <div className="chip-scroll" role="group" aria-label="Filtrer par catégorie">
          <Chip selected={flaggedOnly} onClick={() => setFlaggedOnly((v) => !v)}>
            À surveiller
          </Chip>
          {CATEGORY_ORDER.map((c) => (
            <Chip key={c} selected={categories.includes(c)} icon={CATEGORY_ICON[c]} onClick={() => toggleCategory(c)}>
              {CATEGORY_SHORT[c]}
            </Chip>
          ))}
        </div>
        <Segmented<SourceFilter>
          label="Origine"
          value={source}
          onChange={setSource}
          options={[
            { value: "all", label: "Tout" },
            { value: "caregiver_voice", label: "Vous" },
            { value: "auxiliary_report", label: "Auxiliaire" },
            { value: "wearable", label: "Bracelet" },
          ]}
        />
      </div>

      <div className="result-line">
        <span aria-live="polite">{plural(filtered.length, "observation", "observations")}</span>
        <span style={{ display: "flex", gap: 2 }}>
          {hasFilters ? (
            <Button variant="ghost" size="sm" icon={FunnelX} onClick={resetFilters}>
              Effacer
            </Button>
          ) : null}
          <Button variant="ghost" size="sm" icon={ArrowUpDown} onClick={() => setNewestFirst((v) => !v)} aria-label={newestFirst ? "Trier du plus ancien au plus récent" : "Trier du plus récent au plus ancien"}>
            {newestFirst ? "Récent d'abord" : "Ancien d'abord"}
          </Button>
        </span>
      </div>

      {groups.length === 0 ? (
        <EmptyState
          icon={CalendarRange}
          title={hasFilters ? "Rien ne correspond à ces filtres" : period === "1" ? "Rien de consigné aujourd'hui" : "Aucune observation sur cette période"}
          action={
            hasFilters ? (
              <Button variant="secondary" onClick={resetFilters}>
                Réinitialiser les filtres
              </Button>
            ) : undefined
          }
        >
          {hasFilters
            ? "Élargissez la période ou retirez un filtre pour retrouver les faits."
            : "Les faits apparaîtront ici dès votre prochain compte rendu ou le prochain passage de l'auxiliaire."}
        </EmptyState>
      ) : (
        <>
          {groups.slice(0, visibleDays).map((g) => (
            <section key={g.day} className="day-group" aria-labelledby={`day-${g.day}`}>
              <div className="day-head">
                <h2 id={`day-${g.day}`}>{relativeDay(`${g.day}T12:00:00`)}</h2>
                <span>{plural(g.list.length, "fait", "faits")}</span>
              </div>
              <ol className="tl">
                {g.list.map((o) => (
                  <TimelineItem key={o.id} o={o} />
                ))}
              </ol>
            </section>
          ))}
          {groups.length > visibleDays ? (
            <div style={{ marginTop: 16 }}>
              <Button block variant="secondary" onClick={() => setVisibleDays((v) => v + PAGE_DAYS)}>
                Afficher les jours précédents
              </Button>
            </div>
          ) : null}
        </>
      )}
    </>
  );
}
