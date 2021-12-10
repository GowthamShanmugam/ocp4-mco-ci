import * as React from 'react';
import Status, { StatusPopupSection } from '@odf/shared/popup/status-popup';
import { HealthState } from '@openshift-console/dynamic-plugin-sdk';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@patternfly/react-icons';

export type SystemHealthMap = {
  systemName: string;
  healthState: HealthState;
  link: string;
};

type StorageSystemPopopProps = {
  systemHealthMap: SystemHealthMap[];
};

const healthStateToIcon = {
  [HealthState.OK]: (
    <CheckCircleIcon color="var(--pf-global--primary-color--100)" />
  ),
  [HealthState.ERROR]: (
    <ExclamationCircleIcon color="var(--pf-global--danger-color--100)" />
  ),
};

const StorageSystemPopup: React.FC<StorageSystemPopopProps> = ({
  systemHealthMap,
}) => {
  const { t } = useTranslation('plugin__odf-console');
  return (
    <StatusPopupSection
      firstColumn={t('Storage System')}
      secondColumn={t('Health')}
    >
      {systemHealthMap.map((system) => (
        <Status
          key={system.systemName}
          icon={healthStateToIcon[system.healthState]}
        >
          <Link to={system.link}>{system.systemName}</Link>
        </Status>
      ))}
    </StatusPopupSection>
  );
};

export default StorageSystemPopup;
