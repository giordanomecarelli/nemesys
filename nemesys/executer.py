# executer.py
# -*- coding: utf-8 -*-

# Copyright (c) 2011-2016 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import logging
import platform
from datetime import datetime
from threading import Event
from time import sleep
import traceback
import os

from common import client, ntptime, _generated_version, utils
from common import iptools
from common import nem_exceptions
from common import paths
from common.deliverer import Deliverer
from common.nem_exceptions import SysmonitorException, TaskException
from common.proof import Proof
from common.scheduler import Scheduler
from common.tester import Tester
from nemesys import gui_server
from nemesys import nem_options
from nemesys import restart
from nemesys.measure import Measure
from nemesys.sysmonitor import SysProfiler


if not utils.is_windows():
    from daemon import daemon, pidfile

logger = logging.getLogger(__name__)

TH_TRAFFIC = 0.1
MAX_ERRORS = 3
SLEEP_SECS_AFTER_TASK = 30


class Executer(object):
    def __init__(self, client, scheduler, deliverer, sys_profiler,
                 polling=300.0, tasktimeout=60,
                 testtimeout=30, isprobe=True):

        self._client = client
        self._scheduler = scheduler
        self._deliverer = deliverer
        self._sys_profiler = sys_profiler
        self._polling = polling
        self._tasktimeout = tasktimeout
        self._testtimeout = testtimeout
        self._isprobe = isprobe

        self._outbox = paths.OUTBOX_DIR
        self._sent = paths.SENT_DIR
        self._wakeup_event = Event()

        self._time_to_stop = False


    def _do_task(self, task, dev):
        """
        Esegue il complesso di test prescritti dal task
        In presenza di errori ri-tenta per un massimo di 5 volte
        """
        logger.info('Inizio task di misura verso il server %s', task.server)
        try:
            t = Tester(dev=dev, host=task.server, timeout=self._testtimeout)
            # TODO: Pensare ad un'altra soluzione per la generazione
            # del progressivo di misura
            start = datetime.fromtimestamp(ntptime.timestamp())
            m_id = start.strftime('%y%m%d%H%M')
            m = Measure(m_id, task.server,
                        self._client, _generated_version.__version__,
                        start.isoformat())

            for test_type in ['ping', 'download', 'upload']:
                if test_type == 'ping':
                    n_reps = task.ping
                    self._gui_server.measure(test_type)
                    sleep_secs = 1
                elif test_type == "download":
                    n_reps = task.download
                    if n_reps > 0:
                        self._gui_server.measure(test_type, self._client.profile.download / 1000)
                    sleep_secs = 10
                else:
                    n_reps = task.upload
                    if n_reps > 0:
                        self._gui_server.measure(test_type, self._client.profile.upload / 1000)
                    sleep_secs = 10
                proofs = self._do_tests(test_type, n_reps, sleep_secs, t)
                m.add_proofs(proofs)
            sec = datetime.fromtimestamp(ntptime.timestamp()).strftime('%S')
            f = open('%s/measure_%s%s.xml' % (self._outbox, m.id, sec), 'w')
            f.write(str(m))
            f.write('\n<!-- [finished] %s -->'
                    % datetime.fromtimestamp(ntptime.timestamp()).isoformat())
            f.close()

            try:
                self._deliverer.upload_and_move(f.name,
                                                self._sent,
                                                (not self._isprobe))
            except Exception as e:
                self._gui_server.notification(nem_exceptions.DELIVERY_ERROR,
                                              'Misura terminata ma non salvata. %s' % str(e))
            logger.info('Fine task di misura.')

        except Exception as e:
            logger.error('Task interrotto per eccezione durante l\'esecuzione di un test: %s',
                         str(e), exc_info=True)
            error_code = nem_exceptions.errorcode_from_exception(e)
            self._gui_server.notification(error_code, str(e))

    def _do_tests(self, test_type, n_reps, sleep_secs, t):
        proofs = []
        i = 1
        upload_bw = self._client.profile.upload * 1000
        download_bw = self._client.profile.download * 1000
        while i <= n_reps:
            n_errors = 0
            while n_errors < MAX_ERRORS:
                if n_errors > 0:
                    logger.info('Misura in ripresa '
                                'dopo sospensione per errore.')
                logger.info("Esecuzione Test %d su %d di %s", i, n_reps, test_type)
                self._gui_server.test(test_type, i, n_reps, (n_errors > 0))
                try:
                    if test_type == 'ping':
                        proof = t.testping()
                        logger.info('Ping result: %.3f', proof.duration)
                        self._gui_server.speed(proof.duration)
                        if i == n_reps:
                            self._gui_server.result(test_type, proof.duration)
                    elif test_type == 'download':
                        proof = t.testhttpdown(self.callback_httptest, bw=download_bw)
                        kbps = proof.bytes_tot * 8.0 / proof.duration
                        logger.info('Download result: %.3f kbps', kbps)
                        logger.info('Percentuale di traffico spurio: %.2f%%', proof.spurious * 100)
                        self._check_spurious_traffic(proof)
                        result = int(proof.bytes_tot * 8.0 / proof.duration)
                        self._gui_server.result(test_type,
                                                result=result,
                                                spurious=proof.spurious)
                    else:
                        proof = t.testhttpup(self.callback_httptest, upload_bw)
                        kbps = proof.bytes_tot * 8.0 / proof.duration
                        logger.info('Upload result: %.3f kbps', kbps)
                        logger.info('Percentuale di traffico spurio: %.2f%%', proof.spurious * 100)
                        self._check_spurious_traffic(proof)
                        res = int(proof.bytes_tot * 8.0 / proof.duration)
                        self._gui_server.result(test_type,
                                                result=res,
                                                spurious=proof.spurious)
                    proofs.append(proof)
                    break
                except Exception as e:
                    n_errors += 1
                    if n_errors >= MAX_ERRORS:
                        logger.warning('Il massimo numero di errori è stato raggiunto, sospendo la misura')
                        if self._isprobe:
                            proof = Proof(test_type=test_type,
                                          start_time=datetime.now(),
                                          duration=0,
                                          errorcode=nem_exceptions.errorcode_from_exception(e))
                            proofs.append(proof)
                            break
                        else:
                            raise e
                    else:
                        logger.warning('Misura sospesa per eccezione, e\' errore n. %d: %s', n_errors, e, exc_info=True)
                        self._gui_server.result(test_type, error=str(e))
                sleep(sleep_secs)
            sleep(sleep_secs)
            i += 1
        return proofs

    def _handle_task(self, task):
        """
          Follows the directions found in the task
        """
        if task.now:
            secs_to_next_measurement = 0
        else:
            delta = task.start - datetime.fromtimestamp(ntptime.timestamp())
            secs_to_next_measurement = delta.days * 86400 + delta.seconds
        if task.is_wait or secs_to_next_measurement > self._polling + 30:
            # Should just sleep and then download task again
            if task.is_wait:
                wait_secs = task.delay
            else:
                wait_secs = self._polling
                logger.debug('Prossimo task tra: %s minuti'
                             % (secs_to_next_measurement / 60))
            logger.info('Faccio una pausa per %d minuti (%d secondi)', wait_secs / 60, wait_secs)
            logger.debug('Trovato messaggio: %s', task.message)
            self._gui_server.wait(wait_secs, task.message)
            self._sleep_and_wait(wait_secs)
        else:
            # Should execute task after secs_to_next_measurement
            # If there is a message, send it to the GUI
            if task.message:
                self._gui_server.notification(0, task.message)
            if secs_to_next_measurement >= 0:
                if task.download > 0 or task.upload > 0 or task.ping > 0:
                    logger.debug('Impostazione di un nuovo task tra: %d minuti', secs_to_next_measurement / 60)
                    self._sleep_and_wait(secs_to_next_measurement)
                    if self._isprobe:
                        dev = iptools.get_dev(task.server.ip, 80)
                    else:
                        dev = self._profile_system(task.server.ip, 80)
                    if dev:
                        self._do_task(task, dev)
                else:
                    logger.warning('Ricevuto task senza azioni da svolgere')
            else:
                logger.warning('Tempo di attesa prima della misura anomalo: '
                            '%d minuti', secs_to_next_measurement / 60)

    def _profile_system(self, server_ip, port):
        """
        :param server_ip: IP address of measurement server
        :param port: port number on which to connect (e.g. 80)
        :return: the local device for Internet traffic
        """
        self._gui_server.profilation()
        try:
            self._sys_profiler.checkall(self.callback_sys_prof)
            sleep(1)
            self._gui_server.profilation(done=True)
            dev = iptools.get_dev(server_ip, port)
            return dev
        except SysmonitorException as e:
            logger.error('La profilazione del sistema ha rivelato un problema: %s', e)
            sleep(2)
            self._gui_server.profilation(done=True)
            return None

    def _sleep_and_wait(self, seconds):
        event_status = self._wakeup_event.wait(seconds)
        if event_status is True:
            logger.debug('Ricevuto evento durante attesa')
            self._wakeup_event.clear()

    def _check_spurious_traffic(self, test):
        """
        Check that spurious traffic is not too high
        """
        if not self._isprobe:
            if test.spurious < 0:
                raise Exception('Errore durante la verifica del traffico di '
                                'misura: impossibile salvare i dati.')
            if test.spurious >= TH_TRAFFIC:
                raise Exception('Eccessiva presenza di traffico non '
                                'legato alla misura: percentuali {}%.'.format(round(test.spurious * 100)))

    def callback_sys_prof(self, resource, status, info="", errorcode=0):
        # Is called by sysmonitor for each resource
        if status is True:
            status = 'ok'
        else:
            status = 'error'
        logger.debug('Callback dal system profiler: %s, %s, %s', resource, status, info)
        self._gui_server.sys_res(resource, status, info)
        if status == 'error':
            self._gui_server.notification(errorcode, message=info)

    def callback_httptest(self, second, speed):
        """
        Is called by the tester each second.
        Speed is in kbps
        """
        self._gui_server.speed(speed / 1000.0)

    def loop(self):
        """
        Main loop.
        """
        try:
            if self._isprobe:
                logger.info('Inizializzato software per sonda.')
                self._gui_server = gui_server.DummyGuiServer()
            else:
                logger.info('Inizializzato software per misure d\'utente con ISP id = %s', self._client.isp.id)
                logger.info('Con profilo [%s]', self._client.profile)
                self._gui_server = gui_server.Communicator(serial=self._client.id,
                                                           logdir=paths.LOG_DIR,
                                                           version=_generated_version.__version__)
                self._gui_server.start()
            try:
                self._sys_profiler.log_interfaces()
            except Exception as e:
                msg = 'Impossibile rilevare le schede di rete: {}'.format(e)
                logger.error(msg, exc_info=True)
                self._gui_server.notification(nem_exceptions.FAILPROF, message=msg)
            while not self._time_to_stop:
                logger.debug('Inizio del loop principale')
                if self._isprobe:
                    # Try to send any unsent measures (only probe)
                    self._deliverer.uploadall_and_move(self._outbox, self._sent, do_remove=False)
                # Try to download task
                task = None
                tries = 0
                while not task:
                    try:
                        task = self._scheduler.download_task()
                    except TaskException as e:
                        tries += 1
                        if tries >= 3:
                            logger.error('Impossibile scaricare il task: %s', e)
                            self._gui_server.notification(nem_exceptions.TASK_ERROR, message=str(e))
                            break
                if task:
                    # Task found, now do it
                    logger.info('Trovato task %s', task)
                    try:
                        self._handle_task(task)
                    except Exception as e:
                        logger.error('Errore durante la gestione del task per le misure: %s', e, exc_info=True)
                        self._gui_server.notification(nem_exceptions.TASK_ERROR, message=str(e))
                # TODO: check if this is how it is supposed to be
                self._gui_server.wait(SLEEP_SECS_AFTER_TASK,
                                      'Aspetto {} secondi prima di continuare'.format(SLEEP_SECS_AFTER_TASK))
                sleep(SLEEP_SECS_AFTER_TASK)
            logger.info('Uscita dal loop')
            if self._gui_server:
                self._gui_server.stop(5.0)
        except Exception as e:
            logging.critical(f"Exception in main loop: {e}")
            logging.critical(traceback.format_exc())
            logging.critical("Exiting in 5 seconds")
            sleep(5)
            os._exit(1)


    def stop(self):
        self._time_to_stop = True


def get_log_streams(from_logger):
    """ Get a list of filehandle numbers from logger
        to be handed to DaemonContext.files_preserve
    """
    handles = []
    for handler in from_logger.handlers:
        handles.append(handler.stream.fileno())
    if from_logger.parent:
        handles += get_log_streams(from_logger.parent)
    return handles


def main():
    from nemesys import log_conf
    log_conf.init_log()

    logger.info('Avvio di Nemesys v.%s on %s', _generated_version.FULL_VERSION, platform.platform())
    logger.info('Pacchetto Nemesys generato su %s in data %s', _generated_version.PLATFORM,
                _generated_version.__updated__)
    paths.create_nemesys_dirs()
    (options, _, md5conf) = nem_options.parse_args(_generated_version.__version__)
    logger.debug(f"Ricevuta configurazione: {options}")

    c = client.getclient(options)
    isprobe = (c.isp.certificate is not None)
    sys_profiler = SysProfiler(c.profile.upload,
                               c.profile.download,
                               c.isp.id, bypass=not options.killonerror)

    e = Executer(client=c,
                 scheduler=Scheduler(options.scheduler,
                                     c,
                                     md5conf,
                                     _generated_version.__version__,
                                     options.httptimeout),
                 deliverer=Deliverer(options.repository,
                                     c.isp.certificate,
                                     options.httptimeout),
                 sys_profiler=sys_profiler,
                 polling=options.polling,
                 tasktimeout=options.tasktimeout,
                 testtimeout=options.testtimeout,
                 isprobe=isprobe)

    restart_scheduler = restart.RestartScheduler()
    restart_scheduler.start()

    if not utils.is_linux():
        logger.debug('Inizio il loop.')
        e.loop()
    else:
        logger.info('Avvio il demone Nemesys')
        pidf = pidfile.TimeoutPIDLockFile(options.pidfile, -1)
        log_streams = get_log_streams(logger)
        context = daemon.DaemonContext(
            working_directory=paths._APP_DIR,
            pidfile=pidf,
            files_preserve=log_streams,
        )
        # TODO: context.signal_map = {signal.SIGTERM: do_exit}
        # But need to fix sleep wakeup etc first
        with context:
            e.loop()
            logger.info('Loop exit')


if __name__ == '__main__':
    main()
