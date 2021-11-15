"""
FILE: mayaviviewerfieldworkmodel.py
LAST MODIFIED: 24-12-2015 
DESCRIPTION: Container class for fieldwork meshes in a mayavi scene.

===============================================================================
This file is part of GIAS2. (https://bitbucket.org/jangle/gias2)

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
===============================================================================
"""
import logging

import numpy as np

from gias3.fieldwork.field import geometric_field
from gias3.mapclientpluginutilities.viewers.mayaviviewerobjects import MayaviViewerSceneObject, MayaviViewerObject, colours

log = logging.getLogger(__name__)


class MayaviViewerFieldworkModelSceneObject(MayaviViewerSceneObject):
    typeName = 'fieldworkmodel'

    def __init__(self, name, mesh, points, elem_lines=None):
        super().__init__()
        self.name = name
        self.mesh = mesh
        self.points = points
        self.elemLines = elem_lines

    def setVisibility(self, mesh_visible, points_visible, lines_visible):
        if self.mesh:
            self.mesh.visible = mesh_visible
        if self.points:
            self.points.visible = points_visible
        if self.elemLines:
            self.elemLines = lines_visible

    def remove(self):
        if self.mesh:
            self.mesh.remove()
            self.mesh = None

        if self.points:
            self.points.remove()
            self.points = None

        if self.elemLines:
            self.elemLines.remove()
            self.elemLines = None


class MayaviViewerFieldworkModel(MayaviViewerObject):
    typeName = 'fieldworkmodel'

    def __init__(self, name, model, discrete, evaluator=None, render_args=None, fields=None, field_name=None, PC=None, display_gf_nodes=False, merge_gf_vertices=False):
        super().__init__()
        self.name = name
        self.model = model
        self.discrete = discrete

        if evaluator is None:
            self.evaluator = geometric_field.makeGeometricFieldEvaluatorSparse(self.model, self.discrete)
        else:
            self.evaluator = evaluator

        self.renderArgs = {} if render_args is None else render_args
        self._fields = {} if fields is None else fields

        self.fieldName = field_name
        self.PC = PC
        self.sceneObject = None
        self._uniqueVertexIndices = None
        self.mergeGFVertices = merge_gf_vertices
        self.displayGFNodes = display_gf_nodes
        self.defaultColour = colours['bone']
        if 'color' not in list(self.renderArgs.keys()):
            self.renderArgs['color'] = self.defaultColour

    def setScalarSelection(self, field_name):
        self.fieldName = field_name

    def setVisibility(self, visible):
        self.sceneObject.setVisibility(visible, self.displayGFNodes & visible, visible)

    def remove(self):
        self.sceneObject.remove()
        self.sceneObject = None

    def draw(self, scene):
        scene.disable_render = True
        P = self.evaluator(self.model.get_field_parameters().ravel())

        mayaviMesh = None
        # calc scalar
        S = None
        if self.fieldName != 'none':
            if self.fieldName == 'mean curvature':
                K, H, k1, k2 = self.model.evaluate_curvature_in_mesh(self.discrete)
                S = H
            elif self.fieldName == 'gaussian curvature':
                K, H, k1, k2 = self.model.evaluate_curvature_in_mesh(self.discrete)
                S = K
            else:
                # check if S is a field that needs evaluating - TODO
                S = self._fields.get(self.fieldName)

        # draw
        if self.model.EnsembleFieldFunction.dimensions == 2:
            # triangulate vertices
            T = self.model.triangulator._triangulate(self.discrete)

            if self.mergeGFVertices:
                log.debug(np.unique(T).shape)
                log.debug(np.where(P == 0.0)[0].shape)

                P, T, self._uniqueVertexIndices, vertMap = self.model.triangulator._mergePoints2(P.T)
                P = P.T

                log.debug(np.unique(T).shape)
                log.debug(np.where(P == 0.0)[0].shape)

                if S is not None:
                    S = S[self._uniqueVertexIndices]

            if (S is None) or (S == 'none'):
                log.debug('S = None')
                mayaviMesh = scene.mlab.triangular_mesh(P[0], P[1], P[2], T, name=self.name, **self.renderArgs)
            else:
                log.debug(S)
                mayaviMesh = scene.mlab.triangular_mesh(P[0], P[1], P[2], T, scalars=S, name=self.name,
                                                        **self.renderArgs)

        elif self.model.EnsembleFieldFunction.dimensions == 1:
            mayaviMesh = self.model._draw_curve([self.discrete[0]], name=self.name, **self.renderArgs)

        mayaviPoints = self._plot_points(scene)
        if not self.displayGFNodes:
            mayaviPoints.visible = False

        self.sceneObject = MayaviViewerFieldworkModelSceneObject(self.name, mayaviMesh, mayaviPoints)
        scene.disable_render = False

        return self.sceneObject

    def _plot_points(self, scene, glyph='sphere', label=None, scale=0.5):
        """ uses mayavi points3d to show the positions of all points 
        (with labels if label is true)
        
        label can be 'all', or 'landmarks'
        """

        # get point positions
        p = np.array(self.model.get_all_point_positions())

        if len(p) > 0:
            s = np.arange(len(p))
            points_plot = scene.mlab.points3d(p[:, 0], p[:, 1], p[:, 2], s, mode='sphere', scale_mode='none',
                                              scale_factor=scale, color=(1, 0, 0))

            # label all ensemble points with their index number
            if label == 'all':
                labels = list(range(len(p)))
                for i in range(len(labels)):
                    l = scene.mlab.text(p[i, 0], p[i, 1], str(labels[i]), z=p[i, 2], line_width=0.01,
                                        width=0.005 * len(str(labels[i])) ** 1.1)

            elif label == 'landmarks':
                m = self.model.named_points_map
                labels = list(m.keys())
                for label in labels:
                    l = scene.mlab.text(p[m[label]][0], p[m[label]][1], label, z=p[m[label]][2], line_width=0.01,
                                        width=0.005 * len(label) ** 1.1)
            return points_plot
        else:
            raise ValueError('model has no nodes')

    def updateGeometry(self, params, scene):

        if params is None:
            params = self.model.field_parameters

        if self.sceneObject is None:
            self.model.set_field_parameters(params)
            self.draw(scene)
        else:
            V = self.evaluator(params)
            p = params.reshape((3, -1))

            if self.mergeGFVertices:
                V = V[:, self._uniqueVertexIndices]

            self.sceneObject.mesh.mlab_source.set(x=V[0], y=V[1], z=V[2])
            self.sceneObject.points.mlab_source.set(x=p[0], y=p[1], z=p[2])

    def updateScalar(self, field_name, scene):
        self.setScalarSelection(field_name)
        if self.sceneObject is None:
            self.model.set_field_parameters(params)
            self.draw(scene)
        else:
            scalar = self._fields[self.fieldName]

            if scalar is None:
                if 'color' not in self.renderArgs:
                    colour = self.defaultColour
                else:
                    colour = self.renderArgs['color']

                self.sceneObject.mesh.actor.mapper.scalar_visibility = False
                self.sceneObject.mesh.actor.property.specular_color = colour
                self.sceneObject.mesh.actor.property.diffuse_color = colour
                self.sceneObject.mesh.actor.property.ambient_color = colour
                self.sceneObject.mesh.actor.property.color = colour
            else:
                if self.mergeGFVertices:
                    scalar = scalar[self._uniqueVertexIndices]
                self.sceneObject.mesh.mlab_source.set(scalars=scalar)
                self.sceneObject.mesh.actor.mapper.scalar_visibility = True

    # def drawElementBoundaries( self, name, GD, evaluatorMaker, nNodesElemMap, elemBasisMap, renderArgs ):
    #     g = self.geometricFields[name]

    #     self.bCurves[name] = {}
    #     for elemN in self.model.ensemble_field_function.mesh.elements.keys():
    #         self.bCurves[name][name+'_elem_'+str(elemN)] = self.model.makeElementBoundaryCurve( elemN, nNodesElemMap, elemBasisMap )

    #     for b in self.bCurves[name]:
    #         evaluator = evaluatorMaker( self.bCurves[name][b], GD )
    #         self.addGeometricField( b, self.bCurves[name][b], evaluator, GD, renderArgs )
    #         self._drawGeometricField( b )

    # def hideElementBoundaries( self, name ):
    #     for b in self.bCurves[name]:
    #         SOb = self.sceneObjectGF.get(b)
    #         if SOb!=None:
    #             SOb.visible=False

    # def showElementBoundaries( self, name ):
    #     for b in self.bCurves[name]:
    #         SOb = self.sceneObjectGF.get(b)
    #         if SOb!=None:
    #             SOb.visible=True
