import * as React from 'react';
import { DRPC_STATUS } from '@odf/mco/constants';
import { PlacementInfo, ProtectedAppMap } from '@odf/mco/types';
import { getDRStatus, getPageRange } from '@odf/mco/utils';
import { utcDateTimeFormatter } from '@odf/shared/details-page/datetime';
import { fromNow } from '@odf/shared/details-page/datetime';
import { URL_POLL_DEFAULT_DELAY } from '@odf/shared/hooks/custom-prometheus-poll/use-url-poll';
import { useCustomTranslation } from '@odf/shared/useCustomTranslationHook';
import {
  PrometheusResponse,
  RowProps,
  StatusIconAndText,
  TableColumn,
  TableData,
  VirtualizedTable,
  useActiveColumns,
} from '@openshift-console/dynamic-plugin-sdk';
import { TFunction } from 'i18next';
import {
  Pagination,
  PaginationVariant,
  Text,
  TextVariants,
} from '@patternfly/react-core';
import { sortable } from '@patternfly/react-table';
import { StatusText } from './common';

const INITIAL_PAGE_NUMBER = 1;
const COUNT_PER_PAGE_NUMBER = 5;

export const getCurrentActivity = (
  currentStatus: string,
  failoverCluster: string,
  preferredCluster: string,
  t: TFunction
) => {
  if (
    [DRPC_STATUS.Relocating, DRPC_STATUS.Relocated].includes(
      currentStatus as DRPC_STATUS
    )
  ) {
    return t('{{ currentStatus }} to {{ preferredCluster }}', {
      currentStatus,
      preferredCluster,
    });
  } else if (
    [DRPC_STATUS.FailingOver, DRPC_STATUS.FailedOver].includes(
      currentStatus as DRPC_STATUS
    )
  ) {
    return t('{{ currentStatus }} to {{ failoverCluster }}', {
      currentStatus,
      failoverCluster,
    });
  } else {
    return t('Unknown');
  }
};

const getSubscriptionRow = (
  selectedApp: ProtectedAppMap
): SubscriptionRowProps[] =>
  selectedApp?.placementInfo?.reduce(
    (acc, placement) => [
      ...acc,
      ...placement?.subscriptions?.map((name) => ({
        name,
        activity: placement?.status,
        lastSnapshotSyncTime: placement?.lastGroupSyncTime,
        failoverCluster: placement?.failoverCluster,
        preferredCluster: placement?.preferredCluster,
      })),
    ],
    []
  ) || [];

const tableColumns = [
  {
    className: '',
    id: 'name',
  },
  {
    className: '',
    id: 'activity',
  },
  {
    className: '',
    id: 'lastSnapshotSyncTime',
  },
];

const subscriptionsTableColumns = (
  t: TFunction
): TableColumn<SubscriptionRowProps>[] => [
  {
    title: t('Name'),
    sort: 'name',
    transforms: [sortable],
    props: {
      className: tableColumns[0].className,
    },
    id: tableColumns[0].id,
  },
  {
    title: t('Activity'),
    sort: 'activity',
    transforms: [sortable],
    props: {
      className: tableColumns[1].className,
    },
    id: tableColumns[1].id,
  },
  {
    title: t('Last snapshot synced'),
    sort: 'lastSnapshotSyncTime',
    transforms: [sortable],
    props: {
      className: tableColumns[2].className,
    },
    id: tableColumns[2].id,
  },
];

export const ActivitySection: React.FC<CommonProps> = ({ selectedApp }) => {
  const { t } = useCustomTranslation();

  const placementInfo: PlacementInfo = selectedApp?.placementInfo?.[0];
  const currentStatus = placementInfo?.status;
  const failoverCluster = placementInfo?.failoverCluster;
  const preferredCluster = placementInfo?.preferredCluster;
  return (
    <div className="mco-dashboard__contentColumn">
      <StatusText>{t('Activity')}</StatusText>
      <StatusIconAndText
        icon={getDRStatus({ currentStatus, t }).icon}
        title={getCurrentActivity(
          currentStatus,
          failoverCluster,
          preferredCluster,
          t
        )}
        className="text-muted"
      />
    </div>
  );
};

export const SnapshotSection: React.FC<CommonProps> = ({ selectedApp }) => {
  const { t } = useCustomTranslation();
  const [lastSyncTime, setLastSyncTime] = React.useState('N/A');
  const lastGroupSyncTime = selectedApp?.placementInfo?.[0]?.lastGroupSyncTime;
  const clearSetIntervalId = React.useRef<NodeJS.Timeout>();
  const updateSyncTime = React.useCallback(() => {
    if (!!lastGroupSyncTime) {
      const dateTime = utcDateTimeFormatter.format(new Date(lastGroupSyncTime));
      setLastSyncTime(`${dateTime} (${fromNow(lastGroupSyncTime)})`);
    } else {
      setLastSyncTime('N/A');
    }
  }, [lastGroupSyncTime]);

  React.useEffect(() => {
    updateSyncTime();
    clearSetIntervalId.current = setInterval(
      updateSyncTime,
      URL_POLL_DEFAULT_DELAY
    );
    return () => clearInterval(clearSetIntervalId.current);
  }, [updateSyncTime]);

  return (
    <div className="mco-dashboard__contentColumn">
      <StatusText>{t('Snapshot')}</StatusText>
      <Text className="text-muted">
        {t('Last replicated on: {{ lastSyncTime }}', {
          lastSyncTime: lastSyncTime,
        })}
      </Text>
    </div>
  );
};

const SubscriptionRow: React.FC<RowProps<SubscriptionRowProps>> = ({
  obj: {
    name,
    activity,
    lastSnapshotSyncTime,
    failoverCluster,
    preferredCluster,
  },
  activeColumnIDs,
}) => {
  const { t } = useCustomTranslation();
  const lastSnapshotSyncTimeStr =
    !!lastSnapshotSyncTime &&
    utcDateTimeFormatter.format(new Date(lastSnapshotSyncTime));
  return (
    <>
      <TableData {...tableColumns[0]} activeColumnIDs={activeColumnIDs}>
        {name}
      </TableData>
      <TableData {...tableColumns[1]} activeColumnIDs={activeColumnIDs}>
        {getCurrentActivity(activity, failoverCluster, preferredCluster, t)}
      </TableData>
      <TableData {...tableColumns[2]} activeColumnIDs={activeColumnIDs}>
        {lastSnapshotSyncTimeStr || t('Unknown')}
      </TableData>
    </>
  );
};

export const SubscriptionSection: React.FC<SubscriptionSectionProps> = ({
  selectedApp,
}) => {
  const { t } = useCustomTranslation();
  const subsCount = selectedApp?.placementInfo?.reduce(
    (acc, placement) => acc + placement?.subscriptions?.length,
    0
  );
  return (
    <div className="mco-dashboard__contentColumn">
      <Text component={TextVariants.h1}>{subsCount}</Text>
      <StatusText>{t('Subscription')}</StatusText>
    </div>
  );
};

export const SubscriptionDetailsSection: React.FC<SubscriptionDetailsSectionProps> =
  ({ selectedApp }) => {
    const { t } = useCustomTranslation();
    const [page, setPage] = React.useState(INITIAL_PAGE_NUMBER);
    const [perPage, setPerPage] = React.useState(COUNT_PER_PAGE_NUMBER);
    const [start, end] = getPageRange(page, perPage);
    const subscriptionRow: SubscriptionRowProps[] =
      getSubscriptionRow(selectedApp);
    const paginatedRows = subscriptionRow.slice(start, end);
    const [columns] = useActiveColumns({
      columns: subscriptionsTableColumns(t),
      showNamespaceOverride: false,
      columnManagementID: null,
    });

    return (
      <div className="mco-dashboard__contentColumn">
        <Text component={TextVariants.h3}>{t('Subscription details')}</Text>
        <div className="mco-cluster-app__subscription-table">
          <VirtualizedTable
            data={paginatedRows}
            unfilteredData={paginatedRows}
            aria-label={t('Storage Clients')}
            columns={columns}
            Row={SubscriptionRow}
            loaded={true}
            loadError=""
          />
          <Pagination
            perPageComponent="button"
            itemCount={subscriptionRow?.length}
            widgetId="subscription-table"
            perPage={perPage}
            page={page}
            variant={PaginationVariant.bottom}
            perPageOptions={[]}
            isStatic
            onSetPage={(_event, newPage) => setPage(newPage)}
            onPerPageSelect={(_event, newPerPage, newPage) => {
              setPerPage(newPerPage);
              setPage(newPage);
            }}
          />
        </div>
      </div>
    );
  };

type CommonProps = {
  selectedApp: ProtectedAppMap;
  lastSyncTimeData?: PrometheusResponse;
};

type SubscriptionSectionProps = {
  selectedApp: ProtectedAppMap;
};

type SubscriptionDetailsSectionProps = {
  selectedApp: ProtectedAppMap;
};

type SubscriptionRowProps = {
  name: string;
  activity: string;
  lastSnapshotSyncTime: string;
  failoverCluster: string;
  preferredCluster: string;
};
