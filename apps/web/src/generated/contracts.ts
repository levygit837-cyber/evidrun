/* Generated from Pydantic JSON Schema. Do not edit by hand. */

export type CatalogV1 =
  | StudyRevision
  | GoalRevision
  | ScenarioRevision
  | AgentInventoryRevision
  | WorkspaceTemplateRevision
  | InteractionProtocolRevision
  | EvaluationPlanRevision
  | CheckpointPolicyRevision
  | RunSpec
  | AdmissionRecord
  | SubjectEnvelope
  | EvaluationRecord
  | EvaluatorEnvelope
  | CheckpointRecord
  | RevisionDecisionRecord
  | RunRecord
  | RunQueuedPayload
  | RunPreparingPayload
  | RunLifecyclePayload
  | ContextComposedPayload
  | SubjectInvokedPayload
  | SubjectRespondedPayload
  | EvaluationCompletedPayload
  | CapabilityOfferedPayload
  | SkillLoadedPayload
  | CapabilityInvocationPayload
  | CapabilityResultPayload
  | ToolCalledPayload
  | ToolDecisionPayload
  | ToolResultPayload
  | CheckpointValidationFailedPayload
  | RunTerminalPayload;
export type ContractType = "study";
export type LogicalId = string;
export type BaselineVariant = string;
export type CandidateVariant = string;
export type PrimaryVariable = string;
export type Comparisons = ComparisonPlan[];
export type EvidenceMode =
  | "prospective_controlled"
  | "counterfactual_replay"
  | "retrospective_observational"
  | "exploratory";
export type ContractType1 =
  | "study"
  | "goal"
  | "scenario"
  | "agent_inventory"
  | "workspace_template"
  | "interaction_protocol"
  | "evaluation_plan"
  | "checkpoint_policy";
export type Digest = string;
export type LogicalId1 = string;
export type Revision = number;
export type Assumptions = string[];
export type DecisionToInform = string | null;
export type Hypothesis = string | null;
export type Purpose = string;
export type Questions = string[];
export type Excluded = string[];
export type Included = string[];
export type Limitations = string[];
export type Repetitions = number;
export type MaxCost = number | null;
export type MaxInputTokens = number | null;
export type MaxOutputTokens = number | null;
export type MaxToolCalls = number | null;
export type MaxTurns = number | null;
export type MaxWallSeconds = number;
export type DefaultMode = "metadata" | "redacted" | "raw_encrypted" | "disabled";
export type RawSensitive = "disabled" | "opt_in";
export type SensitiveTtlDays = number;
export type Id = string;
export type MaxChars = number;
export type Strategy = "head" | "tail" | "full";
export type Classification = "public" | "internal" | "sensitive" | "restricted";
export type Digest1 = string;
export type Namespace = string;
export type ArtifactId = string;
export type Classification1 = "public" | "internal" | "sensitive" | "restricted";
export type Digest2 = string;
export type Locator = string | null;
export type MediaType = string;
export type Required = boolean;
export type SchemaVersion = string;
export type Slot = string;
export type Extensions = ExtensionRef[];
export type Action = "terminal" | "pause";
export type Kind =
  | "goal_complete"
  | "bounded_exploration_complete"
  | "budget_exhausted"
  | "human_stop"
  | "guardrail_violation"
  | "provider_error"
  | "predicate";
export type Digest3 = string;
export type Name = string;
export type Namespace1 = string;
export type Version = string;
export type StopConditions = StopCondition[];
export type ScenarioRefs = ContractRef[];
export type Kind1 = "deterministic" | "fixed" | "per_repetition";
export type Seed = number | null;
export type Tags = string[];
export type Confounders = string[];
export type Id1 = string;
export type Label = string;
export type Notes = string | null;
export type Extensions1 = ExtensionRef[] | null;
export type StopConditions1 = StopCondition[] | null;
export type Variants = VariantSpec[];
export type ProjectId = string;
export type Revision1 = number;
export type SchemaVersion1 = "1";
export type Title = string;
export type ContractType2 = "goal";
export type LogicalId2 = string;
export type CompletionObservations = string[];
export type Description = string;
export type Id2 = string;
export type Rule = "must" | "must_not";
export type Constraints = GoalConstraint[];
export type EvidenceExpectations = string[];
export type Instruction = string;
export type LearningTargets = string[];
export type Mode = "goal_state" | "bounded_exploration";
export type Description1 = string;
export type Id3 = string;
export type Outcomes = GoalOutcome[];
export type ProjectId1 = string;
export type Revision2 = number;
export type SchemaVersion2 = "1";
export type Title1 = string;
export type ContractType3 = "scenario";
export type LogicalId3 = string;
export type Description2 = string;
export type Id4 = string;
export type MountAccess = "read_only" | "read_write";
export type MountName = string | null;
export type Role = string;
export type Visibility = "subject" | "evaluator" | "laboratory" | "subject_and_evaluator";
export type InputBindings = InputBinding[];
export type Limitations1 = string[];
export type ObservableConditions = string[];
export type Provenance = string[];
export type ProjectId2 = string;
export type Revision3 = number;
export type SchemaVersion3 = "1";
export type Title2 = string;
export type ContractType4 = "agent_inventory";
export type LogicalId4 = string;
export type AuthorityConstraints = string[];
export type Exposure = "schema_only" | "instructions" | "instructions_and_schema";
export type InstructionRefs = ArtifactRef[];
export type Kind2 = "tool" | "skill";
export type MinimumInterfaceVersion = string;
export type RequestedPermissions = string[];
export type Required1 = boolean;
export type CapabilityRequirements = CapabilityRequirement[];
export type ProviderProfileId = string | null;
export type Capability = string;
export type Required2 = boolean;
export type RuntimeRequirements = RuntimeRequirement[];
export type SubjectId = string;
export type ProjectId3 = string;
export type Revision4 = number;
export type SchemaVersion4 = "1";
export type Title3 = string;
export type ContractType5 = "workspace_template";
export type LogicalId5 = string;
export type Mode1 = "discard" | "retain_until_ttl" | "retain";
export type TtlSeconds = number | null;
export type AllowedEffects = string[];
export type Mode2 = "denied" | "approval_required" | "allowlist";
export type Lifecycle = "ephemeral_per_run";
export type Access = "read_only" | "read_write";
export type Name1 = string;
export type Target = string;
export type Mounts = WorkspaceMount[];
export type AllowedEndpointRefs = string[];
export type Mode3 = "disabled" | "provider_only" | "allowlist";
export type RuntimeKind = string;
export type BindingId = string;
export type Source = "keychain" | "environment";
export type SecretBindingRefs = SecretBindingRef[];
export type CaptureWorkspace = boolean;
export type IncludeZones = string[];
export type WriteZones = string[];
export type ProjectId4 = string;
export type Revision5 = number;
export type SchemaVersion5 = "1";
export type Title4 = string;
export type ContractType6 = "interaction_protocol";
export type LogicalId6 = string;
export type MaxActivations = number;
export type Priority = number;
export type Source1 = string;
export type Target1 = string;
export type Trigger =
  | AlwaysTrigger
  | EventTrigger
  | CheckpointReachedTrigger
  | EvaluatorSignalTrigger
  | HumanSignalTrigger
  | PredicateTrigger;
export type Kind3 = "always";
export type EventType = string;
export type Kind4 = "event";
export type CheckpointDefinitionId = string;
export type Kind5 = "checkpoint_reached";
export type Kind6 = "evaluator_signal";
export type Signal = string;
export type StageId = string;
export type Kind7 = "human_signal";
export type Signal1 = string;
export type Kind8 = "predicate";
export type Edges = InteractionEdge[];
export type InitialMessageRefs = ArtifactRef[];
export type MaxTurns1 = number;
export type Mode4 = "single_turn" | "graph";
export type Id5 = string;
export type Kind9 = "prompt" | "await_subject" | "checkpoint" | "human_approval" | "terminal";
export type Nodes = InteractionNode[];
export type ProjectId5 = string;
export type Revision6 = number;
export type SchemaVersion6 = "1";
export type Title5 = string;
export type ContractType7 = "evaluation_plan";
export type LogicalId7 = string;
export type Key = string;
export type Value = string | number | boolean;
export type Parameters = KeyValue[];
export type HiddenFields = string[];
export type Anchors = KeyValue[];
export type Description3 = string;
export type Id6 = string;
export type Maximum = number | null;
export type Minimum = number | null;
export type ValueType = "boolean" | "number" | "category";
export type Dimensions = EvaluationDimension[];
export type HiddenInputRefs = ArtifactRef[];
export type PublicDimensionIds = string[];
export type Authority = string;
export type Required3 = boolean;
export type Limitations2 = string[];
export type HardGate = boolean;
export type Id7 = string;
export type Kind10 = "integrity" | "deterministic_grader" | "model_judge" | "human_review";
export type OutputDimensions = string[];
export type Parameters1 = KeyValue[];
export type Kind11 = "run_terminal" | "checkpoint" | "event";
export type Reference = string | null;
export type VisibleToSubject = boolean;
export type Stages = EvaluationStage[];
export type ProjectId6 = string;
export type Revision7 = number;
export type SchemaVersion7 = "1";
export type Title6 = string;
export type ContractType8 = "checkpoint_policy";
export type LogicalId8 = string;
export type AgentInventory = boolean;
export type ArtifactManifest = boolean;
export type ContextSnapshot = boolean;
export type EvaluationRecords = boolean;
export type ProtocolState = boolean;
export type ProviderResolution = boolean;
export type WorkspaceSnapshot = boolean;
export type CompatibilityTags = string[];
export type Id8 = string;
export type Label1 = string;
export type Order = number;
export type Required4 = boolean;
export type Trigger1 =
  | ManualCheckpointTrigger
  | CheckpointEventTrigger
  | ProtocolNodeCheckpointTrigger
  | PredicateCheckpointTrigger;
export type Kind12 = "manual";
export type EventType1 = string;
export type Kind13 = "event";
export type Kind14 = "protocol_node";
export type NodeId = string;
export type Kind15 = "predicate";
export type ValidatorRefs = CapabilityDescriptorRef[];
export type Definitions = CheckpointDefinition[];
export type ProjectId7 = string;
export type Revision8 = number;
export type SchemaVersion8 = "1";
export type Title7 = string;
export type Extensions2 = ExtensionRef[];
export type Limitations3 = string[];
export type RepetitionIndex = number;
export type SchemaVersion9 = "1";
export type Seed1 = number | null;
export type StopConditions2 = StopCondition[];
export type VariantId = string;
export type CreatedAtUtc = string;
export type Decision = "admitted" | "rejected";
export type DeniedPolicies = string[];
export type InteractionStatus = "resolved" | "unsupported";
export type Blocking = boolean;
export type Category =
  "runner" | "provider" | "capability" | "runtime" | "workspace" | "interaction" | "policy";
export type Code = "unsupported" | "denied" | "unavailable" | "digest_mismatch";
export type Detail = string;
export type SubjectRef = string;
export type Issues = AdmissionIssue[];
export type MissingRequirements = string[];
export type Adapter = string | null;
export type ContextRefs = ArtifactRef[];
export type EffectiveInterfaceVersion = string | null;
export type EffectivePermissions = string[];
export type Exposure1 = "schema_only" | "instructions" | "instructions_and_schema";
export type Kind16 = "tool" | "skill";
export type Required5 = boolean;
export type SatisfiedAuthorityConstraints = string[];
export type Status = "resolved" | "unsupported" | "denied" | "unavailable";
export type Capabilities = ResolvedCapability[];
export type ProviderAdapter = string | null;
export type ProviderModel = string | null;
export type ProviderProfileDigest = string | null;
export type ProviderProfileId1 = string | null;
export type ProviderReasoningEffort = string | null;
export type RuntimeCapabilities = string[];
export type RunSpecDigest = string;
export type RunSpecRef = string;
export type SchemaVersion10 = "1";
export type Warnings = string[];
export type WorkspaceStatus = "resolved" | "unsupported" | "denied" | "unavailable";
export type EffectiveCapabilities = ResolvedCapability[];
export type Inputs = InputBinding[];
export type RunSpecDigest1 = string;
export type SchemaVersion11 = "1";
export type StopConditions3 = StopCondition[];
export type ExternalEffectMode = "denied" | "approval_required" | "allowlist";
export type Mounts1 = string[];
export type NetworkMode = "disabled" | "provider_only" | "allowlist";
export type RuntimeKind1 = string;
export type WriteZones1 = string[];
export type CheckpointId = string | null;
export type EventHash = string | null;
export type UpToEventSequence = number | null;
export type CreatedAtUtc1 = string;
export type Confidence = number | null;
export type DimensionId = string;
/**
 * @minItems 1
 */
export type EvidenceRefs = [EvidenceRef, ...EvidenceRef[]];
export type Ref = string;
export type Rationale = string;
export type Value1 = string | number | boolean;
export type DimensionValues = DimensionValue[];
export type GateStatus = "passed" | "failed" | "not_applicable";
export type ProviderModel1 = string | null;
export type ProviderProfileId2 = string | null;
export type RecordId = string;
export type RunId = string;
export type SchemaVersion12 = "1";
export type SourceType = "deterministic_grader" | "model_judge" | "human_adjudicator";
export type StageId1 = string;
export type Status1 = "provisional" | "final";
export type SupersedesRecordRef = string | null;
export type BlindedFields = string[];
export type Dimensions1 = EvaluationDimension[];
export type HiddenInputRefs1 = ArtifactRef[];
export type Inputs1 = InputBinding[];
export type RunSpecDigest2 = string;
export type SchemaVersion13 = "1";
export type AdmissionRecordDigest = string | null;
export type AdmissionRecordId = string | null;
export type CheckpointId1 = string;
export type CompatibilityTags1 = string[];
export type ContextSnapshotRefs = string[];
export type CreatedAtUtc2 = string;
export type DefinitionDigest = string;
export type DefinitionId = string;
export type EvaluationRecordRefs = string[];
export type EventHash1 = string;
export type Replayability = "none" | "partial" | "deterministic";
export type ReplayabilityLimitations = string[];
export type RunId1 = string;
export type SchemaVersion14 = "1";
export type UpToEventSequence1 = number;
export type EvidenceRefs1 = EvidenceRef[];
export type Passed = boolean;
export type Rationale1 = string;
export type Validations = CheckpointValidation[];
export type ActorId = string;
export type ActorType = "human";
export type DecidedAtUtc = string;
export type Decision1 = "accepted" | "rejected" | "superseded";
export type Rationale2 = string;
export type SchemaVersion15 = "1";
export type AdmissionDigest = string;
export type AdmissionId = string;
export type CreatedAtUtc3 = string;
export type RepetitionIndex1 = number;
export type RetryOf = string | null;
export type RunId2 = string;
export type RunSpecDigest3 = string;
export type RunSpecId = string;
export type SchemaVersion16 = "1";
export type VariantId1 = string;
export type AdmissionDigest1 = string;
export type RunId3 = string;
export type RunSpecDigest4 = string;
export type VariantId2 = string;
export type FromStatus = "queued" | "preparing" | "running" | "paused" | "evaluating";
export type Reason = string;
export type ContentHash = string;
export type Omitted = boolean;
export type PolicyId = string;
export type SelectedChars = number;
export type SnapshotId = string;
export type SourceChars = number;
export type Strategy1 = "head" | "tail" | "full";
export type Network = "disabled" | "provider_only" | "allowlist";
export type Runner = string;
export type SubjectEnvelopeDigest = string;
export type CaptureMode = "metadata" | "redacted" | "raw_encrypted" | "disabled";
export type Evidence = string[];
export type Metadata = KeyValue[];
export type Output = string | null;
export type OutputDigest = string;
export type EvaluationRecordDigest = string;
export type EvaluationRecordId = string;
export type GateStatus1 = "passed" | "failed" | "not_applicable";
export type EffectivePermissions1 = string[];
export type Exposure2 = "schema_only" | "instructions" | "instructions_and_schema";
export type Required6 = boolean;
export type InstructionRefs1 = ArtifactRef[];
export type InvocationId = string;
export type InvocationId1 = string;
export type Reason1 = string | null;
export type CallId = string;
export type InputDigest = string;
export type CallId1 = string;
export type DecidedBy = string;
export type Rationale3 = string;
export type CallId2 = string;
export type Reason2 = string | null;
export type CheckpointDefinitionId1 = string;
export type EvidenceRefs2 = EvidenceRef[];
export type Rationale4 = string;
export type CheckpointRefs = string[];
export type EvaluationRecordRefs1 = string[];
export type GoalState = "achieved" | "partially_achieved" | "not_achieved" | "not_assessable";
export type Status2 =
  "completed" | "failed" | "cancelled" | "budget_exhausted" | "guardrail_stopped";
export type TerminalCause = string;

export interface StudyRevision {
  contract_type?: ContractType;
  logical_id: LogicalId;
  payload: StudySpec;
  project_id: ProjectId;
  revision: Revision1;
  schema_version?: SchemaVersion1;
  title: Title;
}
export interface StudySpec {
  comparisons?: Comparisons;
  evidence_mode: EvidenceMode;
  goal_ref: ContractRef;
  intent: StudyIntent;
  limitations?: Limitations;
  repetitions?: Repetitions;
  run_blueprint: RunBlueprint;
  scenario_refs: ScenarioRefs;
  seed_strategy?: SeedStrategy;
  tags?: Tags;
  variants?: Variants;
}
export interface ComparisonPlan {
  baseline_variant: BaselineVariant;
  candidate_variant: CandidateVariant;
  primary_variable: PrimaryVariable;
}
export interface ContractRef {
  contract_type: ContractType1;
  digest: Digest;
  logical_id: LogicalId1;
  revision: Revision;
}
export interface StudyIntent {
  assumptions?: Assumptions;
  decision_to_inform?: DecisionToInform;
  hypothesis?: Hypothesis;
  purpose: Purpose;
  questions?: Questions;
  scope?: IntentScope;
}
export interface IntentScope {
  excluded?: Excluded;
  included?: Included;
}
export interface RunBlueprint {
  agent_inventory_ref: ContractRef;
  budgets: BudgetSpec;
  capture_policy: CapturePolicySpec;
  checkpoint_policy_ref?: ContractRef | null;
  context_policy?: ContextPolicySpec | null;
  evaluation_plan_ref: ContractRef;
  extensions?: Extensions;
  interaction_protocol_ref: ContractRef;
  stop_conditions: StopConditions;
  workspace_template_ref: ContractRef;
}
export interface BudgetSpec {
  max_cost?: MaxCost;
  max_input_tokens?: MaxInputTokens;
  max_output_tokens?: MaxOutputTokens;
  max_tool_calls?: MaxToolCalls;
  max_turns?: MaxTurns;
  max_wall_seconds: MaxWallSeconds;
}
export interface CapturePolicySpec {
  default_mode: DefaultMode;
  raw_sensitive?: RawSensitive;
  sensitive_ttl_days?: SensitiveTtlDays;
}
export interface ContextPolicySpec {
  id: Id;
  max_chars: MaxChars;
  strategy: Strategy;
}
export interface ExtensionRef {
  classification: Classification;
  digest: Digest1;
  namespace: Namespace;
  payload_ref: ArtifactRef;
  required?: Required;
  schema_ref: ArtifactRef;
  schema_version: SchemaVersion;
  slot: Slot;
}
export interface ArtifactRef {
  artifact_id: ArtifactId;
  classification?: Classification1;
  digest: Digest2;
  locator?: Locator;
  media_type: MediaType;
}
export interface StopCondition {
  action?: Action;
  kind: Kind;
  predicate_ref?: CapabilityDescriptorRef | null;
}
export interface CapabilityDescriptorRef {
  digest: Digest3;
  name: Name;
  namespace: Namespace1;
  version: Version;
}
export interface SeedStrategy {
  kind: Kind1;
  seed?: Seed;
}
export interface VariantSpec {
  confounders?: Confounders;
  id: Id1;
  label: Label;
  notes?: Notes;
  overrides?: VariantOverrides;
}
export interface VariantOverrides {
  agent_inventory_ref?: ContractRef | null;
  budgets?: BudgetSpec | null;
  capture_policy?: CapturePolicySpec | null;
  checkpoint_policy_ref?: ContractRef | null;
  context_policy?: ContextPolicySpec | null;
  evaluation_plan_ref?: ContractRef | null;
  extensions?: Extensions1;
  goal_ref?: ContractRef | null;
  interaction_protocol_ref?: ContractRef | null;
  scenario_ref?: ContractRef | null;
  stop_conditions?: StopConditions1;
  workspace_template_ref?: ContractRef | null;
}
export interface GoalRevision {
  contract_type?: ContractType2;
  logical_id: LogicalId2;
  payload: GoalSpec;
  project_id: ProjectId1;
  revision: Revision2;
  schema_version?: SchemaVersion2;
  title: Title1;
}
export interface GoalSpec {
  completion_observations?: CompletionObservations;
  constraints?: Constraints;
  evidence_expectations?: EvidenceExpectations;
  instruction: Instruction;
  learning_targets?: LearningTargets;
  mode: Mode;
  outcomes?: Outcomes;
}
export interface GoalConstraint {
  description: Description;
  id: Id2;
  rule: Rule;
}
export interface GoalOutcome {
  description: Description1;
  id: Id3;
}
export interface ScenarioRevision {
  contract_type?: ContractType3;
  logical_id: LogicalId3;
  payload: ScenarioSpec;
  project_id: ProjectId2;
  revision: Revision3;
  schema_version?: SchemaVersion3;
  title: Title2;
}
export interface ScenarioSpec {
  description: Description2;
  input_bindings: InputBindings;
  limitations?: Limitations1;
  observable_conditions?: ObservableConditions;
  provenance?: Provenance;
}
export interface InputBinding {
  id: Id4;
  mount_access?: MountAccess;
  mount_name?: MountName;
  role: Role;
  source: ArtifactRef;
  visibility: Visibility;
}
export interface AgentInventoryRevision {
  contract_type?: ContractType4;
  logical_id: LogicalId4;
  payload: AgentInventorySpec;
  project_id: ProjectId3;
  revision: Revision4;
  schema_version?: SchemaVersion4;
  title: Title3;
}
export interface AgentInventorySpec {
  capability_requirements?: CapabilityRequirements;
  provider_profile_id?: ProviderProfileId;
  runner_ref: CapabilityDescriptorRef;
  runtime_requirements?: RuntimeRequirements;
  subject_id: SubjectId;
}
export interface CapabilityRequirement {
  authority_constraints?: AuthorityConstraints;
  capability_ref: CapabilityDescriptorRef;
  exposure: Exposure;
  instruction_refs?: InstructionRefs;
  kind: Kind2;
  minimum_interface_version: MinimumInterfaceVersion;
  requested_permissions?: RequestedPermissions;
  required?: Required1;
}
export interface RuntimeRequirement {
  capability: Capability;
  required?: Required2;
}
export interface WorkspaceTemplateRevision {
  contract_type?: ContractType5;
  logical_id: LogicalId5;
  payload: WorkspaceTemplateSpec;
  project_id: ProjectId4;
  revision: Revision5;
  schema_version?: SchemaVersion5;
  title: Title4;
}
export interface WorkspaceTemplateSpec {
  cleanup_policy?: CleanupPolicy;
  external_effect_policy: ExternalEffectPolicy;
  lifecycle?: Lifecycle;
  mounts?: Mounts;
  network_policy: NetworkPolicy;
  runtime_kind: RuntimeKind;
  secret_binding_refs?: SecretBindingRefs;
  snapshot_policy?: SnapshotPolicy;
  write_zones?: WriteZones;
}
export interface CleanupPolicy {
  mode?: Mode1;
  ttl_seconds?: TtlSeconds;
}
export interface ExternalEffectPolicy {
  allowed_effects?: AllowedEffects;
  mode: Mode2;
}
export interface WorkspaceMount {
  access: Access;
  name: Name1;
  source: ArtifactRef;
  target: Target;
}
export interface NetworkPolicy {
  allowed_endpoint_refs?: AllowedEndpointRefs;
  mode: Mode3;
}
export interface SecretBindingRef {
  binding_id: BindingId;
  source: Source;
}
export interface SnapshotPolicy {
  capture_workspace?: CaptureWorkspace;
  include_zones?: IncludeZones;
}
export interface InteractionProtocolRevision {
  contract_type?: ContractType6;
  logical_id: LogicalId6;
  payload: InteractionProtocolSpec;
  project_id: ProjectId5;
  revision: Revision6;
  schema_version?: SchemaVersion6;
  title: Title5;
}
export interface InteractionProtocolSpec {
  edges?: Edges;
  initial_message_refs?: InitialMessageRefs;
  max_turns?: MaxTurns1;
  mode: Mode4;
  nodes?: Nodes;
  system_prompt_ref?: ArtifactRef | null;
}
export interface InteractionEdge {
  max_activations?: MaxActivations;
  priority?: Priority;
  source: Source1;
  target: Target1;
  trigger: Trigger;
}
export interface AlwaysTrigger {
  kind?: Kind3;
}
export interface EventTrigger {
  event_type: EventType;
  kind?: Kind4;
}
export interface CheckpointReachedTrigger {
  checkpoint_definition_id: CheckpointDefinitionId;
  kind?: Kind5;
}
export interface EvaluatorSignalTrigger {
  kind?: Kind6;
  signal: Signal;
  stage_id: StageId;
}
export interface HumanSignalTrigger {
  kind?: Kind7;
  signal: Signal1;
}
export interface PredicateTrigger {
  kind?: Kind8;
  predicate_ref: CapabilityDescriptorRef;
}
export interface InteractionNode {
  content_ref?: ArtifactRef | null;
  id: Id5;
  kind: Kind9;
}
export interface EvaluationPlanRevision {
  contract_type?: ContractType7;
  logical_id: LogicalId7;
  payload: EvaluationPlanSpec;
  project_id: ProjectId6;
  revision: Revision7;
  schema_version?: SchemaVersion7;
  title: Title6;
}
export interface EvaluationPlanSpec {
  aggregation?: AggregationSpec | null;
  blinding_policy?: BlindingPolicy;
  dimensions: Dimensions;
  disclosure?: EvaluationDisclosure;
  human_adjudication_policy?: HumanAdjudicationPolicy;
  limitations?: Limitations2;
  stages: Stages;
}
export interface AggregationSpec {
  parameters?: Parameters;
  projector_ref: CapabilityDescriptorRef;
}
export interface KeyValue {
  key: Key;
  value: Value;
}
export interface BlindingPolicy {
  hidden_fields?: HiddenFields;
}
export interface EvaluationDimension {
  anchors?: Anchors;
  description: Description3;
  id: Id6;
  maximum?: Maximum;
  minimum?: Minimum;
  value_type: ValueType;
}
export interface EvaluationDisclosure {
  hidden_input_refs?: HiddenInputRefs;
  public_dimension_ids?: PublicDimensionIds;
}
export interface HumanAdjudicationPolicy {
  authority?: Authority;
  required?: Required3;
}
export interface EvaluationStage {
  evaluator_ref: CapabilityDescriptorRef;
  hard_gate?: HardGate;
  id: Id7;
  kind: Kind10;
  output_dimensions?: OutputDimensions;
  parameters?: Parameters1;
  trigger: EvaluationTrigger;
  visible_to_subject?: VisibleToSubject;
}
export interface EvaluationTrigger {
  kind: Kind11;
  reference?: Reference;
}
export interface CheckpointPolicyRevision {
  contract_type?: ContractType8;
  logical_id: LogicalId8;
  payload: CheckpointPolicySpec;
  project_id: ProjectId7;
  revision: Revision8;
  schema_version?: SchemaVersion8;
  title: Title7;
}
export interface CheckpointPolicySpec {
  definitions: Definitions;
}
export interface CheckpointDefinition {
  capture: CheckpointCaptureSpec;
  compatibility_tags?: CompatibilityTags;
  id: Id8;
  label: Label1;
  order: Order;
  required?: Required4;
  trigger: Trigger1;
  validator_refs?: ValidatorRefs;
}
export interface CheckpointCaptureSpec {
  agent_inventory?: AgentInventory;
  artifact_manifest?: ArtifactManifest;
  context_snapshot?: ContextSnapshot;
  evaluation_records?: EvaluationRecords;
  protocol_state?: ProtocolState;
  provider_resolution?: ProviderResolution;
  workspace_snapshot?: WorkspaceSnapshot;
}
export interface ManualCheckpointTrigger {
  kind?: Kind12;
}
export interface CheckpointEventTrigger {
  event_type: EventType1;
  kind?: Kind13;
}
export interface ProtocolNodeCheckpointTrigger {
  kind?: Kind14;
  node_id: NodeId;
}
export interface PredicateCheckpointTrigger {
  kind?: Kind15;
  predicate_ref: CapabilityDescriptorRef;
}
export interface RunSpec {
  agent_inventory: AgentInventorySpec;
  agent_inventory_ref: ContractRef;
  budgets: BudgetSpec;
  capture_policy: CapturePolicySpec;
  checkpoint_policy?: CheckpointPolicySpec | null;
  checkpoint_policy_ref?: ContractRef | null;
  context_policy?: ContextPolicySpec | null;
  evaluation_plan: EvaluationPlanSpec;
  evaluation_plan_ref: ContractRef;
  extensions?: Extensions2;
  goal: GoalSpec;
  goal_ref: ContractRef;
  interaction_protocol: InteractionProtocolSpec;
  interaction_protocol_ref: ContractRef;
  limitations?: Limitations3;
  repetition_index: RepetitionIndex;
  scenario: ScenarioSpec;
  scenario_ref: ContractRef;
  schema_version?: SchemaVersion9;
  seed?: Seed1;
  stop_conditions: StopConditions2;
  study_ref: ContractRef;
  variant_id: VariantId;
  workspace: WorkspaceTemplateSpec;
  workspace_template_ref: ContractRef;
}
export interface AdmissionRecord {
  created_at_utc: CreatedAtUtc;
  decision: Decision;
  denied_policies?: DeniedPolicies;
  interaction_status: InteractionStatus;
  issues?: Issues;
  missing_requirements?: MissingRequirements;
  resolved_inventory: ResolvedAgentInventory;
  run_spec_digest: RunSpecDigest;
  run_spec_ref: RunSpecRef;
  schema_version?: SchemaVersion10;
  warnings?: Warnings;
  workspace_status: WorkspaceStatus;
}
export interface AdmissionIssue {
  blocking: Blocking;
  category: Category;
  reason: ResolutionReason;
  subject_ref: SubjectRef;
}
export interface ResolutionReason {
  code: Code;
  detail: Detail;
}
export interface ResolvedAgentInventory {
  capabilities?: Capabilities;
  provider_adapter?: ProviderAdapter;
  provider_model?: ProviderModel;
  provider_profile_digest?: ProviderProfileDigest;
  provider_profile_id?: ProviderProfileId1;
  provider_reasoning_effort?: ProviderReasoningEffort;
  requirement_ref: ContractRef;
  runner_ref: CapabilityDescriptorRef;
  runtime_capabilities?: RuntimeCapabilities;
}
export interface ResolvedCapability {
  adapter?: Adapter;
  context_refs?: ContextRefs;
  effective_interface_version?: EffectiveInterfaceVersion;
  effective_permissions?: EffectivePermissions;
  exposure: Exposure1;
  kind: Kind16;
  reason?: ResolutionReason | null;
  requested_ref: CapabilityDescriptorRef;
  required: Required5;
  resolved_ref?: CapabilityDescriptorRef | null;
  satisfied_authority_constraints?: SatisfiedAuthorityConstraints;
  status: Status;
}
export interface SubjectEnvelope {
  budgets: BudgetSpec;
  effective_capabilities: EffectiveCapabilities;
  goal: GoalSpec;
  inputs: Inputs;
  interaction_protocol: InteractionProtocolSpec;
  run_spec_digest: RunSpecDigest1;
  schema_version?: SchemaVersion11;
  stop_conditions: StopConditions3;
  workspace: SubjectWorkspace;
}
export interface SubjectWorkspace {
  external_effect_mode: ExternalEffectMode;
  mounts?: Mounts1;
  network_mode: NetworkMode;
  runtime_kind: RuntimeKind1;
  write_zones?: WriteZones1;
}
export interface EvaluationRecord {
  boundary: EvaluationBoundary;
  created_at_utc: CreatedAtUtc1;
  dimension_values: DimensionValues;
  evaluator_ref: CapabilityDescriptorRef;
  gate_status: GateStatus;
  plan_ref: ContractRef;
  provider_model?: ProviderModel1;
  provider_profile_id?: ProviderProfileId2;
  record_id: RecordId;
  run_id: RunId;
  schema_version?: SchemaVersion12;
  source_type: SourceType;
  stage_id: StageId1;
  status: Status1;
  supersedes_record_ref?: SupersedesRecordRef;
}
export interface EvaluationBoundary {
  checkpoint_id?: CheckpointId;
  event_hash?: EventHash;
  up_to_event_sequence?: UpToEventSequence;
}
export interface DimensionValue {
  confidence?: Confidence;
  dimension_id: DimensionId;
  evidence_refs: EvidenceRefs;
  rationale: Rationale;
  value: Value1;
}
export interface EvidenceRef {
  ref: Ref;
}
export interface EvaluatorEnvelope {
  blinded_fields?: BlindedFields;
  dimensions: Dimensions1;
  hidden_input_refs?: HiddenInputRefs1;
  inputs: Inputs1;
  plan_ref: ContractRef;
  run_spec_digest: RunSpecDigest2;
  schema_version?: SchemaVersion13;
  stage: EvaluationStage;
}
export interface CheckpointRecord {
  admission_record_digest?: AdmissionRecordDigest;
  admission_record_id?: AdmissionRecordId;
  artifact_manifest_ref?: ArtifactRef | null;
  checkpoint_id: CheckpointId1;
  compatibility_tags?: CompatibilityTags1;
  context_snapshot_refs?: ContextSnapshotRefs;
  created_at_utc: CreatedAtUtc2;
  definition_digest: DefinitionDigest;
  definition_id: DefinitionId;
  evaluation_record_refs?: EvaluationRecordRefs;
  event_hash: EventHash1;
  policy_ref: ContractRef;
  protocol_state_ref?: ArtifactRef | null;
  replayability: Replayability;
  replayability_limitations?: ReplayabilityLimitations;
  run_id: RunId1;
  schema_version?: SchemaVersion14;
  up_to_event_sequence: UpToEventSequence1;
  validations: Validations;
  workspace_snapshot_ref?: ArtifactRef | null;
}
export interface CheckpointValidation {
  evidence_refs?: EvidenceRefs1;
  passed: Passed;
  rationale: Rationale1;
  validator_ref: CapabilityDescriptorRef;
}
export interface RevisionDecisionRecord {
  actor_id: ActorId;
  actor_type?: ActorType;
  decided_at_utc: DecidedAtUtc;
  decision: Decision1;
  rationale: Rationale2;
  revision_ref: ContractRef;
  schema_version?: SchemaVersion15;
}
export interface RunRecord {
  admission_digest: AdmissionDigest;
  admission_id: AdmissionId;
  created_at_utc: CreatedAtUtc3;
  repetition_index: RepetitionIndex1;
  retry_of?: RetryOf;
  run_id: RunId2;
  run_spec_digest: RunSpecDigest3;
  run_spec_id: RunSpecId;
  scenario_ref: ContractRef;
  schema_version?: SchemaVersion16;
  study_ref: ContractRef;
  variant_id: VariantId1;
}
export interface RunQueuedPayload {
  admission_digest: AdmissionDigest1;
  run_id: RunId3;
  run_spec_digest: RunSpecDigest4;
  variant_id: VariantId2;
}
export interface RunPreparingPayload {
  scenario_ref: ContractRef;
}
export interface RunLifecyclePayload {
  from_status: FromStatus;
  reason: Reason;
}
export interface ContextComposedPayload {
  content_hash: ContentHash;
  omitted: Omitted;
  policy_id: PolicyId;
  selected_chars: SelectedChars;
  snapshot_id: SnapshotId;
  source_chars: SourceChars;
  strategy: Strategy1;
}
export interface SubjectInvokedPayload {
  network: Network;
  runner: Runner;
  subject_envelope_digest: SubjectEnvelopeDigest;
}
export interface SubjectRespondedPayload {
  capture_mode: CaptureMode;
  evidence?: Evidence;
  metadata?: Metadata;
  output?: Output;
  output_digest: OutputDigest;
}
export interface EvaluationCompletedPayload {
  evaluation_record_digest: EvaluationRecordDigest;
  evaluation_record_id: EvaluationRecordId;
  gate_status: GateStatus1;
}
export interface CapabilityOfferedPayload {
  capability_ref: CapabilityDescriptorRef;
  effective_permissions?: EffectivePermissions1;
  exposure: Exposure2;
  required: Required6;
}
export interface SkillLoadedPayload {
  capability_ref: CapabilityDescriptorRef;
  instruction_refs?: InstructionRefs1;
}
export interface CapabilityInvocationPayload {
  capability_ref: CapabilityDescriptorRef;
  invocation_id: InvocationId;
}
export interface CapabilityResultPayload {
  capability_ref: CapabilityDescriptorRef;
  invocation_id: InvocationId1;
  reason?: Reason1;
  result_ref?: ArtifactRef | null;
}
export interface ToolCalledPayload {
  arguments_ref?: ArtifactRef | null;
  call_id: CallId;
  capability_ref: CapabilityDescriptorRef;
  input_digest: InputDigest;
}
export interface ToolDecisionPayload {
  call_id: CallId1;
  decided_by: DecidedBy;
  rationale: Rationale3;
}
export interface ToolResultPayload {
  call_id: CallId2;
  capability_ref: CapabilityDescriptorRef;
  reason?: Reason2;
  result_ref?: ArtifactRef | null;
}
export interface CheckpointValidationFailedPayload {
  checkpoint_definition_id: CheckpointDefinitionId1;
  evidence_refs?: EvidenceRefs2;
  rationale: Rationale4;
  validator_ref: CapabilityDescriptorRef;
}
export interface RunTerminalPayload {
  checkpoint_refs?: CheckpointRefs;
  evaluation_record_refs?: EvaluationRecordRefs1;
  goal_state: GoalState;
  status: Status2;
  terminal_cause: TerminalCause;
}
