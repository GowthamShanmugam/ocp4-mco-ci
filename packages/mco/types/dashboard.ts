import { APPLICATION_TYPE, DRPC_STATUS, REPLICATION_TYPE } from '../constants';
import { ACMManagedClusterKind } from '../types';

export type PlacementInfo = Partial<{
  drpcName: string;
  drpcNamespace: string;
  workloadNamespace: string;
  replicationType: REPLICATION_TYPE;
  syncInterval: string;
  deploymentClusterName: string;
  failoverCluster: string;
  preferredCluster: string;
  lastGroupSyncTime: string;
  status: DRPC_STATUS;
  protectedPVCs: string[];
}>;

export type ProtectedAppMap = {
  appName: string;
  appNamespace: string;
  appKind: string;
  appAPIVersion: string;
  appType: APPLICATION_TYPE;
  placementInfo: PlacementInfo[];
};

export type AppObj = {
  namespace: string;
  name: string;
};

export type DRClusterAppsMap = {
  [drClusterName: string]: {
    managedCluster?: ACMManagedClusterKind;
    totalAppCount: number;
    protectedApps: ProtectedAppMap[];
  };
};

export type ProtectedPVCData = {
  drpcName?: string;
  drpcNamespace?: string;
  pvcName?: string;
  pvcNamespace?: string;
  lastSyncTime?: string;
  schedulingInterval?: string;
};
